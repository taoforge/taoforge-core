"""Subnet analysis eval tasks — the self-evaluating improvement loop.

Three tasks form a cycle:
1. SubnetAnalysisTask: Analyze metagraph data
2. SelfEvaluationTask: Rate your own analysis, generate improvement criteria
3. CriteriaEvolutionTask: Re-analyze with self-generated criteria, scored on follow-through
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from taoforge.agent.base import Agent
from taoforge.evaluation.results import TaskScore
from taoforge.evaluation.task import EvalTask
from taoforge.subnets.data import MetagraphSnapshot
from taoforge.subnets.scorers import (
    score_accuracy,
    score_criteria_following,
    score_depth,
    score_self_consistency,
    score_specificity,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisContext:
    """Shared state between the three analysis tasks in a suite run.

    IMPORTANT: Tasks run sequentially in BenchmarkEngine. This object
    is shared by reference — each task reads/writes to pass state forward.
    """

    snapshot: MetagraphSnapshot = field(default_factory=MetagraphSnapshot)
    prior_analysis: str = ""
    prior_score: float = 0.0
    self_eval_rating: float = 0.0
    self_eval_criteria: list[str] = field(default_factory=list)
    round_number: int = 0


class SubnetAnalysisTask(EvalTask):
    """Analyze a subnet metagraph snapshot.

    Score = 0.35 * specificity + 0.35 * accuracy + 0.30 * depth
    """

    category = "subnet_analysis"

    def __init__(
        self,
        task_id: str,
        snapshot: MetagraphSnapshot,
        context: AnalysisContext,
    ) -> None:
        self.task_id = task_id
        self.snapshot = snapshot
        self.context = context
        self.description = f"Subnet analysis: SN{snapshot.netuid}"

    def run(self, agent: Agent) -> TaskScore:
        # Build prompt with metagraph data
        prompt = self._build_prompt()

        result = agent.generate(prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        analysis = result.text

        # Score on three axes
        spec = score_specificity(analysis, self.snapshot)
        acc = score_accuracy(analysis, self.snapshot)
        dep = score_depth(analysis, self.snapshot)

        composite = 0.35 * spec.score + 0.35 * acc.score + 0.30 * dep.score

        # Store in context for subsequent tasks
        self.context.prior_analysis = analysis
        self.context.prior_score = composite

        return TaskScore(
            task_id=self.task_id,
            score=composite,
            metadata={
                "specificity": round(spec.score, 4),
                "accuracy": round(acc.score, 4),
                "depth": round(dep.score, 4),
                "specificity_details": spec.details,
                "accuracy_details": acc.details,
                "depth_details": dep.details,
                "analysis_length": len(analysis),
                "latency_ms": result.latency_ms,
            },
        )

    def _build_prompt(self) -> str:
        summary = self.snapshot.to_prompt_summary(max_neurons=20)

        prompt = (
            "You are analyzing a Bittensor subnet metagraph. "
            "Produce a detailed analysis of the following subnet data.\n\n"
            f"{summary}\n\n"
            "Your analysis should:\n"
            "- Reference specific UIDs and their stake/incentive values\n"
            "- Identify patterns in the data (concentration, anomalies, relationships)\n"
            "- Include accurate numerical values from the data\n"
            "- Analyze the weight matrix and validator-miner dynamics\n"
        )

        # Inject self-generated criteria if available
        if self.context.self_eval_criteria:
            criteria_str = "\n".join(f"- {c}" for c in self.context.self_eval_criteria)
            prompt += (
                f"\nAdditionally, your analysis MUST address these criteria "
                f"(generated from your prior self-evaluation):\n{criteria_str}\n"
            )

        prompt += "\nProvide your analysis:"

        return prompt

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, str) and len(output) > 20


class SelfEvaluationTask(EvalTask):
    """Rate your own analysis and generate improvement criteria.

    Score = self-consistency (calibration between self-rating and objective score)
    """

    category = "subnet_analysis"

    def __init__(
        self,
        task_id: str,
        snapshot: MetagraphSnapshot,
        context: AnalysisContext,
    ) -> None:
        self.task_id = task_id
        self.snapshot = snapshot
        self.context = context
        self.description = f"Self-evaluation: SN{snapshot.netuid}"

    def run(self, agent: Agent) -> TaskScore:
        if not self.context.prior_analysis:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": "no prior analysis"})

        prompt = self._build_prompt()

        result = agent.generate(prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        # Parse self-evaluation
        rating, criteria = self._parse_self_eval(result.text)

        # Normalize rating to [0, 1]
        rating_normalized = rating / 10.0

        # Score on calibration
        consistency = score_self_consistency(rating_normalized, self.context.prior_score)

        # Store in context
        self.context.self_eval_rating = rating_normalized
        self.context.self_eval_criteria = criteria

        return TaskScore(
            task_id=self.task_id,
            score=consistency.score,
            metadata={
                "self_rating": rating,
                "self_rating_normalized": round(rating_normalized, 4),
                "objective_score": round(self.context.prior_score, 4),
                "calibration_error": consistency.details.get("calibration_error", 0),
                "criteria_generated": len(criteria),
                "criteria": criteria,
                "latency_ms": result.latency_ms,
            },
        )

    def _build_prompt(self) -> str:
        # Truncate analysis if too long for context
        analysis = self.context.prior_analysis
        if len(analysis) > 2000:
            analysis = analysis[:2000] + "\n...[truncated]"

        return (
            "You previously produced the following analysis of a Bittensor subnet:\n\n"
            f"{analysis}\n\n"
            "Now evaluate your own analysis:\n"
            "1. Rate the quality of this analysis on a scale of 1-10\n"
            "2. Explain your rating briefly\n"
            "3. List 3-5 specific criteria that would make a BETTER analysis\n\n"
            "Respond in this format:\n"
            "Rating: [1-10]\n"
            "Justification: [brief explanation]\n"
            "Improvement criteria:\n"
            "- [criterion 1]\n"
            "- [criterion 2]\n"
            "- [criterion 3]\n"
        )

    def _parse_self_eval(self, text: str) -> tuple[float, list[str]]:
        """Parse rating and criteria from agent response. Robust fallback parsing."""
        rating = 5.0  # Default if parsing fails
        criteria = []

        # Try JSON parsing first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                rating = float(data.get("rating", 5))
                criteria = data.get("criteria", [])
                if isinstance(criteria, list):
                    criteria = [str(c) for c in criteria]
                return min(max(rating, 1), 10), criteria
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Regex fallback for rating
        rating_match = re.search(r'[Rr]ating[:\s]*(\d+(?:\.\d+)?)', text)
        if rating_match:
            rating = float(rating_match.group(1))
        else:
            # Try "X/10" pattern
            slash_match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', text)
            if slash_match:
                rating = float(slash_match.group(1))

        rating = min(max(rating, 1), 10)

        # Regex fallback for criteria (bullet points)
        # Look for lines starting with - or * or numbered
        criteria_section = text
        criteria_start = re.search(r'(?:criteria|improvement|better|should)[:\s]*\n', text, re.IGNORECASE)
        if criteria_start:
            criteria_section = text[criteria_start.end():]

        for line in criteria_section.split('\n'):
            line = line.strip()
            if re.match(r'^[-*•]\s+', line):
                criterion = re.sub(r'^[-*•]\s+', '', line).strip()
                if len(criterion) > 5:
                    criteria.append(criterion)
            elif re.match(r'^\d+[.)]\s+', line):
                criterion = re.sub(r'^\d+[.)]\s+', '', line).strip()
                if len(criterion) > 5:
                    criteria.append(criterion)

        # Cap at 5 criteria
        criteria = criteria[:5]

        # If no criteria found, generate generic ones
        if not criteria:
            criteria = [
                "Reference specific UIDs with their stake amounts",
                "Include numerical analysis of the weight matrix",
                "Identify concentration or anomaly patterns",
            ]

        return rating, criteria

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, str) and len(output) > 10


class CriteriaEvolutionTask(EvalTask):
    """Re-analyze with self-generated criteria injected. Scores on follow-through.

    Score = 0.25 * specificity + 0.25 * accuracy + 0.20 * depth + 0.30 * criteria_following
    """

    category = "subnet_analysis"

    def __init__(
        self,
        task_id: str,
        snapshot: MetagraphSnapshot,
        context: AnalysisContext,
    ) -> None:
        self.task_id = task_id
        self.snapshot = snapshot
        self.context = context
        self.description = f"Criteria evolution: SN{snapshot.netuid}"

    def run(self, agent: Agent) -> TaskScore:
        if not self.context.self_eval_criteria:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": "no criteria"})

        prompt = self._build_prompt()

        result = agent.generate(prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        new_analysis = result.text

        # Score on four axes
        spec = score_specificity(new_analysis, self.snapshot)
        acc = score_accuracy(new_analysis, self.snapshot)
        dep = score_depth(new_analysis, self.snapshot)
        crit = score_criteria_following(
            self.context.prior_analysis,
            new_analysis,
            self.context.self_eval_criteria,
        )

        composite = (
            0.25 * spec.score
            + 0.25 * acc.score
            + 0.20 * dep.score
            + 0.30 * crit.score
        )

        # Compute improvement over prior analysis
        improvement = composite - self.context.prior_score

        # Update context for potential next round
        self.context.prior_analysis = new_analysis
        self.context.prior_score = composite
        self.context.round_number += 1

        return TaskScore(
            task_id=self.task_id,
            score=composite,
            metadata={
                "specificity": round(spec.score, 4),
                "accuracy": round(acc.score, 4),
                "depth": round(dep.score, 4),
                "criteria_following": round(crit.score, 4),
                "improvement_over_prior": round(improvement, 4),
                "criteria_satisfied": crit.details.get("satisfied", 0),
                "criteria_total": crit.details.get("evaluated", 0),
                "round_number": self.context.round_number,
                "analysis_length": len(new_analysis),
                "latency_ms": result.latency_ms,
            },
        )

    def _build_prompt(self) -> str:
        summary = self.snapshot.to_prompt_summary(max_neurons=20)
        criteria_str = "\n".join(f"- {c}" for c in self.context.self_eval_criteria)

        return (
            "You are re-analyzing a Bittensor subnet metagraph. "
            "Your previous analysis was rated and you identified improvement criteria.\n\n"
            f"METAGRAPH DATA:\n{summary}\n\n"
            f"YOUR SELF-GENERATED IMPROVEMENT CRITERIA:\n{criteria_str}\n\n"
            "Produce a NEW, IMPROVED analysis that specifically addresses each criterion above. "
            "Reference specific UIDs, include accurate numerical values, "
            "and identify non-obvious patterns.\n\n"
            "Provide your improved analysis:"
        )

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, str) and len(output) > 20
