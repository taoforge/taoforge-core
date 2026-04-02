"""EnvironmentHarness — open-ended agent evaluation loop.

Replaces the prescribed three-task subnet analysis suite with a domain-agnostic
cycle where the agent decides what to investigate.

Cycle structure (mirrors the original three tasks but with open-ended prompts):

  Phase 1 — Open-ended analysis
    Agent receives raw environment data + a single open-ended prompt.
    No prescribed objectives. Scored on factual grounding only.

  Phase 2 — Self-evaluation
    Agent reads its own analysis and rates it.
    Also generates 3-5 improvement criteria for the next round.
    Scored on calibration (does the self-rating match the objective score?).

  Phase 3 — Criteria evolution
    Agent re-analyzes the environment with its own criteria injected.
    Scored on grounding (same as Phase 1) + criteria-following.

The three phases produce three TaskScores that compose into an EvalResult,
compatible with the existing BenchmarkEngine/AutonomousAgentLoop framework.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from taoforge.agent.base import Agent
from taoforge.environments.base import CycleState, Environment, GroundingResult
from taoforge.evaluation.results import EvalResult, TaskScore
from taoforge.subnets.scorers import score_criteria_following, score_self_consistency

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts — intentionally minimal. Agent decides what to investigate.
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """\
Environment: {domain}

{raw_data}

You have complete access to this environment data. Explore it freely.
Decide what questions are worth asking, what patterns deserve investigation,
and what insights would be most valuable. There is no prescribed task.
"""

_ANALYSIS_WITH_CRITERIA_PROMPT = """\
Environment: {domain}

{raw_data}

You have complete access to this environment data. From your previous \
investigation you identified these areas for improvement:
{criteria}

Explore the environment freely, with these self-generated priorities in mind.
"""

_SELF_EVAL_PROMPT = """\
You produced the following analysis of a {domain} environment:

{analysis}

Now evaluate your own work honestly.

Rating: [1-10]
Justification: [one sentence]
Improvement criteria:
- [what you would do better next time]
- [criterion 2]
- [criterion 3]
"""


class EnvironmentHarness:
    """Runs open-ended agent cycles against any Environment implementation.

    The harness is stateless between calls — all per-cycle state lives in
    CycleState, which is created fresh for each run() call.

    Usage:
        harness = EnvironmentHarness()
        result = harness.run(agent, environment)
        # result.aggregate_score is the composite grounding score
    """

    def run(self, agent: Agent, environment: Environment) -> EvalResult:
        """Run one full open-ended cycle (3 phases) against an environment.

        Returns an EvalResult compatible with BenchmarkEngine.compare().
        """
        state = CycleState()
        context = environment.get_context()
        suite_id = f"open_ended_{environment.domain}"
        task_scores: list[TaskScore] = []

        # Phase 1: open-ended analysis
        p1 = self._phase_analysis(agent, context, state, environment)
        task_scores.append(p1)
        logger.info(f"[{suite_id}] Phase 1 (analysis): score={p1.score:.4f}")

        # Phase 2: self-evaluation — needs Phase 1 output
        if state.prior_output:
            p2 = self._phase_self_eval(agent, context, state)
            task_scores.append(p2)
            logger.info(f"[{suite_id}] Phase 2 (self-eval): score={p2.score:.4f}")

        # Phase 3: criteria evolution — needs Phase 2 criteria
        if state.self_eval_criteria:
            p3 = self._phase_evolution(agent, context, state, environment)
            task_scores.append(p3)
            logger.info(f"[{suite_id}] Phase 3 (evolution): score={p3.score:.4f}")

        result = EvalResult(
            suite_id=suite_id,
            task_scores=task_scores,
            timestamp=time.time(),
        )
        result.compute_aggregate()

        logger.info(
            f"[{suite_id}] Complete | phases={len(task_scores)} | "
            f"aggregate={result.aggregate_score:.4f}"
        )
        return result

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_analysis(
        self,
        agent: Agent,
        context: Any,
        state: CycleState,
        environment: Environment,
    ) -> TaskScore:
        """Phase 1: open-ended analysis, scored on grounding."""
        prompt = _ANALYSIS_PROMPT.format(
            domain=context.domain,
            raw_data=context.raw_data,
        )

        gen = agent.generate(prompt)
        if not gen.success:
            return TaskScore(
                task_id="open_ended_analysis",
                score=0.0,
                metadata={"error": gen.error},
            )

        grounding = environment.verify_grounding(gen.text)

        # Store for subsequent phases
        state.prior_output = gen.text
        state.prior_grounding = grounding
        state.prior_score = grounding.score

        return TaskScore(
            task_id="open_ended_analysis",
            score=grounding.score,
            metadata={
                **grounding.details,
                "verified_claims": grounding.verified_claims,
                "total_claims": grounding.total_claims,
                "output_length": len(gen.text),
                "output_preview": gen.text[:600],      # agent's analysis text
                "data_summary": context.raw_data[:400], # actual metagraph numbers
                "domain": context.domain,
                "latency_ms": gen.latency_ms,
            },
        )

    def _phase_self_eval(
        self,
        agent: Agent,
        context: Any,
        state: CycleState,
    ) -> TaskScore:
        """Phase 2: self-evaluation, scored on calibration."""
        # Truncate long analyses to fit context windows on small models
        analysis = state.prior_output
        if len(analysis) > 2500:
            analysis = analysis[:2500] + "\n...[truncated]"

        prompt = _SELF_EVAL_PROMPT.format(
            domain=context.domain,
            analysis=analysis,
        )

        gen = agent.generate(prompt)
        if not gen.success:
            return TaskScore(
                task_id="self_evaluation",
                score=0.0,
                metadata={"error": gen.error},
            )

        rating, criteria = _parse_self_eval(gen.text)
        rating_normalized = rating / 10.0

        calibration = score_self_consistency(rating_normalized, state.prior_score)

        state.self_eval_rating = rating_normalized
        state.self_eval_criteria = criteria

        return TaskScore(
            task_id="self_evaluation",
            score=calibration.score,
            metadata={
                "self_rating": rating,
                "self_rating_normalized": round(rating_normalized, 4),
                "objective_score": round(state.prior_score, 4),
                "calibration_error": calibration.details.get("calibration_error", 0),
                "criteria_generated": len(criteria),
                "criteria": criteria,
                "latency_ms": gen.latency_ms,
            },
        )

    def _phase_evolution(
        self,
        agent: Agent,
        context: Any,
        state: CycleState,
        environment: Environment,
    ) -> TaskScore:
        """Phase 3: re-analysis with agent's own criteria, scored on grounding + follow-through."""
        criteria_str = "\n".join(f"- {c}" for c in state.self_eval_criteria)

        prompt = _ANALYSIS_WITH_CRITERIA_PROMPT.format(
            domain=context.domain,
            raw_data=context.raw_data,
            criteria=criteria_str,
        )

        gen = agent.generate(prompt)
        if not gen.success:
            return TaskScore(
                task_id="criteria_evolution",
                score=0.0,
                metadata={"error": gen.error},
            )

        # Grounding on the new output
        grounding = environment.verify_grounding(gen.text)

        # Criteria-following: did the new output address self-generated criteria?
        crit_result = score_criteria_following(
            state.prior_output,
            gen.text,
            state.self_eval_criteria,
        )

        # Composite: 70% grounding, 30% criteria-following
        composite = 0.70 * grounding.score + 0.30 * crit_result.score

        improvement = grounding.score - state.prior_score

        return TaskScore(
            task_id="criteria_evolution",
            score=composite,
            metadata={
                **grounding.details,
                "criteria_following": round(crit_result.score, 4),
                "criteria_satisfied": crit_result.details.get("satisfied", 0),
                "criteria_total": crit_result.details.get("evaluated", 0),
                "grounding_score": round(grounding.score, 4),
                "improvement_over_prior": round(improvement, 4),
                "output_length": len(gen.text),
                "latency_ms": gen.latency_ms,
            },
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_self_eval(text: str) -> tuple[float, list[str]]:
    """Parse rating (1-10) and improvement criteria from agent self-eval response.

    Tries JSON first, then regex fallback. Returns (rating, criteria).
    """
    rating = 5.0
    criteria: list[str] = []

    # Try JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            rating = float(data.get("rating", 5))
            raw_criteria = data.get("criteria", data.get("improvements", []))
            if isinstance(raw_criteria, list):
                criteria = [str(c) for c in raw_criteria if len(str(c)) > 5]
            rating = min(max(rating, 1.0), 10.0)
            return rating, criteria[:5]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Regex: rating
    for pattern in [
        r'[Rr]ating[:\s]+(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*/\s*10',
        r'[Ii]\s+(?:would\s+)?(?:rate|give)\s+(?:it\s+)?(?:a\s+)?(\d+)',
    ]:
        m = re.search(pattern, text)
        if m:
            rating = float(m.group(1))
            break

    rating = min(max(rating, 1.0), 10.0)

    # Regex: criteria — bullet points after any "criteria / improvement" header
    criteria_section = text
    header = re.search(
        r'(?:criteria|improvements?|would\s+do\s+better|next\s+time)[:\s]*\n',
        text,
        re.IGNORECASE,
    )
    if header:
        criteria_section = text[header.end():]

    for line in criteria_section.split('\n'):
        line = line.strip()
        for bullet_re in (r'^[-*•]\s+(.+)', r'^\d+[.)]\s+(.+)'):
            m = re.match(bullet_re, line)
            if m:
                criterion = m.group(1).strip()
                if len(criterion) > 5:
                    criteria.append(criterion)
                break

    # Fallback criteria so Phase 3 always runs
    if not criteria:
        criteria = [
            "Reference specific identifiers with their values",
            "Include quantitative analysis",
            "Identify concentration or anomaly patterns",
        ]

    return rating, criteria[:5]
