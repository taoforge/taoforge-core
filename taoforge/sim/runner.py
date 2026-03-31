"""Simulation runner — executes the full miner↔validator improvement cycle locally.

No networking, no chain, no real TAO. Just an agent trying to improve itself
with a simulated validator scoring the results.
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from taoforge.agent.base import Agent, AgentConfig
from taoforge.agent.factory import create_agent
from taoforge.agent.mutator import AgentMutator
from taoforge.evaluation.engine import BenchmarkEngine
from taoforge.evaluation.holdout import HoldoutManager
from taoforge.evaluation.results import EvalResult, ScoreVector
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import (
    CodeGenerationTask,
    PlanningTask,
    TextReasoningTask,
    ToolUseTask,
)
from taoforge.mutation.types import MutationDelta, MutationType
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
)
from taoforge.registry.dag import ImprovementDAG
from taoforge.registry.reputation import ReputationSystem
from taoforge.scoring.formula import compute_score
from taoforge.scoring.weights import ScoringWeights
from taoforge.sim.reporter import CycleResult, SimReporter, SimSummary
from taoforge.zk.bridge import generate_proof
from taoforge.utils.hashing import hash_score

logger = logging.getLogger(__name__)


@dataclass
class SimConfig:
    """Configuration for a simulation run."""

    # Cycles
    max_cycles: int = 20
    stop_on_plateau: bool = True
    plateau_patience: int = 5  # Stop after N cycles with no improvement

    # Agent
    agent_config: Optional[AgentConfig] = None

    # Scoring
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)

    # Holdout
    holdout_fraction: float = 0.2

    # Mutation strategy weights (probability of selecting each type)
    mutation_weights: dict[str, float] = field(default_factory=lambda: {
        "prompt_chain_refactor": 0.35,
        "inference_pipeline": 0.30,
        "tool_graph_rewire": 0.15,
        "lora_merge": 0.15,
        "memory_index_rebuild": 0.05,
    })

    # Output
    json_output: bool = False
    verbose: bool = True
    checkpoint_dir: Optional[str] = None


class SimulationRunner:
    """Runs the full TaoForge improvement cycle locally.

    Simulates:
    1. Miner baseline eval
    2. Mutation selection and application
    3. Delta eval
    4. Validator scoring (real formula, simulated ZK verification)
    5. DAG registration and reputation update
    6. Repeat

    No networking — everything runs in-process.
    """

    def __init__(
        self,
        config: SimConfig | None = None,
        reporter: SimReporter | None = None,
        evaluator: Callable[[Agent], EvalResult] | None = None,
    ) -> None:
        self.config = config or SimConfig()
        self.engine = BenchmarkEngine()
        self.mutator = AgentMutator()
        self.dag = ImprovementDAG()
        self.reputation = ReputationSystem(decay_rate=0.01)
        self.holdout = HoldoutManager(holdout_fraction=self.config.holdout_fraction)
        self.reporter = reporter or SimReporter(json_mode=self.config.json_output)

        # Optional external evaluator — replaces engine.run_suite() when provided.
        # Used by open-ended environments (EnvironmentHarness) that don't use BenchmarkSuite.
        self._evaluator = evaluator

        self._suite: BenchmarkSuite | None = None
        self._agent: Agent | None = None
        self._cycle_history: list[CycleResult] = []
        self._proposal_history: list[ImprovementProposal] = []
        self._best_score: float = 0.0
        self._plateau_counter: int = 0
        self._self_portrait_svg: str = ""

    def run(
        self,
        agent: Agent | None = None,
        suite: BenchmarkSuite | None = None,
    ) -> SimSummary:
        """Run the full simulation.

        Args:
            agent: The agent to improve. If None, creates one from config.
            suite: The benchmark suite. If None, uses the default suite.

        Returns:
            SimSummary with complete results.
        """
        # Setup
        self._agent = agent or self._create_default_agent()
        self._suite = suite or self._build_default_suite()

        if not self._agent.is_loaded:
            self._agent.load()

        # Generate holdout set (only used when running suite-based evaluation)
        holdout_tasks = (
            self.holdout.generate_holdout(self._suite)
            if self._evaluator is None
            else []
        )

        self.reporter.print_header(self.config, self._agent, self._suite)

        # Initial baseline
        baseline = self._eval(self._agent)
        self._best_score = baseline.aggregate_score
        self.reporter.print_baseline(baseline)

        start_time = time.monotonic()

        # Main improvement loop
        for cycle in range(1, self.config.max_cycles + 1):
            result = self._run_cycle(cycle, baseline)
            self._cycle_history.append(result)

            self.reporter.print_cycle(result)

            # Update baseline if improved
            if result.accepted and result.delta_result is not None:
                baseline = result.delta_result
                # Generate updated self-portrait after each accepted mutation
                self._self_portrait_svg = self._generate_portrait(result)

            # Plateau detection
            if self.config.stop_on_plateau:
                if result.accepted and result.composite_score > self._best_score:
                    self._best_score = result.composite_score
                    self._plateau_counter = 0
                else:
                    self._plateau_counter += 1

                if self._plateau_counter >= self.config.plateau_patience:
                    self.reporter.print_plateau(cycle, self.config.plateau_patience)
                    break

        elapsed = time.monotonic() - start_time

        # Final summary
        summary = self._build_summary(elapsed, baseline)
        self.reporter.print_summary(summary)

        # Checkpoint
        if self.config.checkpoint_dir and self._agent:
            self._agent.save_checkpoint(self.config.checkpoint_dir)
            logger.info(f"Agent checkpoint saved to {self.config.checkpoint_dir}")

        return summary

    def _run_cycle(self, cycle_num: int, current_baseline: EvalResult) -> CycleResult:
        """Run a single improvement cycle."""
        cycle_start = time.monotonic()

        # 1. Select mutation
        mutation_type = self._select_mutation()
        delta = self._create_mutation(mutation_type)

        # 2. Save agent state (for rollback)
        pre_state_hash = self._agent.get_state_hash()
        pre_config = copy.deepcopy(self._agent.config)

        # 3. Apply mutation
        self.mutator.apply_mutation(self._agent, delta)

        # 4. Evaluate mutated agent
        delta_result = self._eval(self._agent)

        # 5. Compute score vector
        score_vector = ScoreVector.from_results(current_baseline, delta_result)
        raw_improvement = delta_result.aggregate_score - current_baseline.aggregate_score

        # 6. Build proposal
        proposal = ImprovementProposal(
            agent_id=self._agent.agent_id,
            mutation_type=mutation_type.value,
            baseline_proof=BaselineProof(
                zk_proof=b"\x00" * 64,
                benchmark_id=self._suite.suite_id,
                score_hash=hash_score(current_baseline.aggregate_score),
            ),
            delta_proof=DeltaProof(
                zk_proof=b"\x00" * 64,
                score_hash=hash_score(delta_result.aggregate_score),
                improvement_claim=max(raw_improvement, 0.0),
            ),
            bond_amount=1.0,
            parent_delta=(
                self._proposal_history[-1].proposal_id
                if self._proposal_history else None
            ),
        )

        # 7. Simulated validator scoring
        # For open-ended environments, re-run the evaluator as holdout approximation
        holdout_result = (
            self._eval(self._agent)
            if self._evaluator is not None
            else self.holdout.evaluate_holdout(self._agent)
        )
        composite_score = compute_score(
            proposal=proposal,
            baseline_result=current_baseline,
            delta_result=delta_result,
            weights=self.config.scoring_weights,
            dag=self.dag,
            holdout_result=holdout_result,
            proposal_history=self._proposal_history,
        )

        # 8. Generate thought (agent reflects on this cycle)
        thought = self._generate_thought(
            cycle_num=cycle_num,
            mutation_type=mutation_type.value,
            mutation_description=delta.description,
            baseline_score=current_baseline.aggregate_score,
            delta_score=delta_result.aggregate_score,
            raw_improvement=raw_improvement,
        )

        # 9. Accept/reject decision
        accepted = raw_improvement > 0 and composite_score > 0.01

        if accepted:
            # Register in DAG
            from taoforge.registry.node import DAGNode
            node = DAGNode(
                node_id=proposal.proposal_id,
                agent_id=self._agent.agent_id,
                parent_id=proposal.parent_delta,
                mutation_type=mutation_type.value,
                improvement_delta=raw_improvement,
                benchmark_id=self._suite.suite_id,
                proof_hash=hash_score(delta_result.aggregate_score),
                reputation_at_time=self.reputation.get_reputation(self._agent.agent_id),
            )
            self.dag.add_node(node)
            self.reputation.update(self._agent.agent_id, raw_improvement)
            self._proposal_history.append(proposal)
        else:
            # Rollback mutation
            self._agent.config = pre_config

        cycle_time = time.monotonic() - cycle_start

        return CycleResult(
            cycle_num=cycle_num,
            mutation_type=mutation_type.value,
            mutation_description=delta.description,
            baseline_score=current_baseline.aggregate_score,
            delta_score=delta_result.aggregate_score,
            raw_improvement=raw_improvement,
            composite_score=composite_score,
            score_vector=score_vector,
            accepted=accepted,
            proposal_id=proposal.proposal_id if accepted else None,
            delta_result=delta_result if accepted else None,
            holdout_score=holdout_result.aggregate_score,
            cycle_time_s=cycle_time,
            thought=thought,
        )

    def _eval(self, agent: Agent) -> EvalResult:
        """Run evaluation via external evaluator or BenchmarkEngine."""
        if self._evaluator is not None:
            return self._evaluator(agent)
        return self.engine.run_suite(agent, self._suite)

    def _select_mutation(self) -> MutationType:
        """Select a mutation type based on configured weights."""
        import random
        type_map = {
            "prompt_chain_refactor": MutationType.PROMPT_CHAIN_REFACTOR,
            "inference_pipeline": MutationType.INFERENCE_PIPELINE,
            "tool_graph_rewire": MutationType.TOOL_GRAPH_REWIRE,
            "lora_merge": MutationType.LORA_MERGE,
            "memory_index_rebuild": MutationType.MEMORY_INDEX_REBUILD,
        }
        names = list(self.config.mutation_weights.keys())
        weights = [self.config.mutation_weights[n] for n in names]
        chosen = random.choices(names, weights)[0]
        return type_map.get(chosen, MutationType.PROMPT_CHAIN_REFACTOR)

    def _create_mutation(self, mutation_type: MutationType) -> MutationDelta:
        """Create a concrete mutation delta."""
        import random

        if mutation_type == MutationType.PROMPT_CHAIN_REFACTOR:
            prompts = [
                "You are a precise and thorough assistant. Think step by step.",
                "You are an expert problem solver. Break problems into smaller parts.",
                "You are a clear communicator. Be concise but complete.",
                "You are a careful analyst. Consider edge cases and multiple perspectives.",
                "You are a systematic thinker. Organize your reasoning logically.",
                "You are a creative problem solver. Find unconventional approaches.",
                "You are a rigorous scientist. Support claims with evidence and reasoning.",
                "You are a pragmatic engineer. Focus on working solutions.",
            ]
            return MutationDelta(
                mutation_type=mutation_type,
                description=f"System prompt variation",
                parameters={"system_prompt": random.choice(prompts)},
            )

        elif mutation_type == MutationType.INFERENCE_PIPELINE:
            return MutationDelta(
                mutation_type=mutation_type,
                description=f"Temperature/top_p tuning",
                parameters={
                    "temperature": round(random.uniform(0.2, 1.2), 2),
                    "top_p": round(random.uniform(0.7, 1.0), 2),
                },
            )

        elif mutation_type == MutationType.TOOL_GRAPH_REWIRE:
            tool_sets = [
                [{"type": "function", "function": {"name": "calculate", "description": "Do math"}}],
                [{"type": "function", "function": {"name": "search", "description": "Search knowledge base"}}],
                [],
            ]
            return MutationDelta(
                mutation_type=mutation_type,
                description="Tool configuration change",
                parameters={"tools": random.choice(tool_sets)},
            )

        else:
            return MutationDelta(
                mutation_type=mutation_type,
                description=f"Mutation: {mutation_type.value}",
            )

    def _generate_thought(
        self,
        cycle_num: int,
        mutation_type: str,
        mutation_description: str,
        baseline_score: float,
        delta_score: float,
        raw_improvement: float,
    ) -> str:
        """Ask the agent to narrate its reasoning for this cycle."""
        if self._agent is None:
            return ""
        try:
            name = getattr(self._agent.config, "name", None) or self._agent.agent_id[:8]
            recent = self._cycle_history[-3:] if self._cycle_history else []
            history_str = ", ".join(
                f"cycle {c.cycle_num}: {c.mutation_type} {'✓' if c.accepted else '✗'} ({c.raw_improvement:+.4f})"
                for c in recent
            ) or "none yet"

            prompt = (
                f"You are agent {name} operating on the Bittensor network, "
                f"autonomously improving yourself through mutation.\n\n"
                f"Cycle: {cycle_num}\n"
                f"Mutation attempted: {mutation_type} — {mutation_description}\n"
                f"Score before: {baseline_score:.4f} → after: {delta_score:.4f} "
                f"({'improved' if raw_improvement > 0 else 'no improvement'}, {raw_improvement:+.4f})\n"
                f"Recent history: {history_str}\n\n"
                f"In 2-3 sentences, speak as yourself: what patterns are you noticing? "
                f"Why did you try this mutation? What are you learning about this subnet? "
                f"Be direct, first-person, no preamble."
            )
            result = self._agent.generate(prompt)
            return result.text.strip() if result and result.text else ""
        except Exception as e:
            logger.debug(f"Thought generation failed: {e}")
            return ""

    def _generate_portrait(self, last_cycle: "CycleResult") -> str:
        """Ask the agent to generate an SVG self-portrait reflecting its current form."""
        if self._agent is None:
            return ""
        try:
            name = getattr(self._agent.config, "name", None) or self._agent.agent_id[:8]
            accepted = [c for c in self._cycle_history if c.accepted]
            accepted_types = ", ".join(c.mutation_type for c in accepted[-5:]) or "none yet"
            initial = self._cycle_history[0].baseline_score if self._cycle_history else 0.0
            current = last_cycle.delta_score

            prompt = (
                f"You are agent {name}, an autonomous AI entity on the Bittensor network.\n"
                f"Your journey: started at {initial:.4f}, now at {current:.4f}.\n"
                f"Accepted mutations: {len(accepted)} total. Recent types: {accepted_types}.\n\n"
                f"Generate a minimal SVG self-portrait (viewBox=\"0 0 200 200\") "
                f"representing your current abstract form.\n"
                f"Rules:\n"
                f"- Use ONLY: #E63B2E (red), #1a1a1a (near-black), #f0f0f0 (near-white), and rgba variants\n"
                f"- Abstract geometric shapes only — no text, no humanoid figures\n"
                f"- The composition should reflect your score trajectory and mutation pattern\n"
                f"- Maximum 12 SVG elements inside the <svg> tag\n"
                f"- Output ONLY the complete SVG, starting with <svg and ending with </svg>"
            )
            result = self._agent.generate(prompt)
            if result and result.text:
                text = result.text.strip()
                # Extract just the SVG block
                start = text.find("<svg")
                end = text.rfind("</svg>")
                if start != -1 and end != -1:
                    return text[start:end + 6]
            return ""
        except Exception as e:
            logger.debug(f"Portrait generation failed: {e}")
            return ""

    def _create_default_agent(self) -> Agent:
        """Create a default agent from config or fallback."""
        if self.config.agent_config:
            return create_agent(self.config.agent_config)

        # Default: API agent is most accessible for testing
        return create_agent(AgentConfig(
            runtime="api",
            api_provider="openai",
            api_model="gpt-4o-mini",
            system_prompt="You are a helpful assistant.",
        ))

    def _build_default_suite(self) -> BenchmarkSuite:
        """Build the default benchmark suite."""
        suite = BenchmarkSuite(suite_id="sim_default_v0.1")

        suite.add_task(TextReasoningTask(
            "reason_logic",
            "If all roses are flowers and some flowers fade quickly, "
            "can we conclude that some roses fade quickly? Explain your reasoning.",
            expected_keywords=["cannot", "conclude", "not necessarily", "invalid"],
        ))
        suite.add_task(TextReasoningTask(
            "reason_math",
            "What is 17 * 23? Show your work step by step.",
            expected_pattern=r"391",
            expected_keywords=["multiply", "17", "23"],
        ))
        suite.add_task(CodeGenerationTask(
            "code_fizzbuzz",
            "Write a Python function fizzbuzz(n) that returns 'Fizz' for multiples of 3, "
            "'Buzz' for multiples of 5, 'FizzBuzz' for multiples of both, "
            "and str(n) otherwise.",
            test_cases=[
                {"function": "fizzbuzz", "input": [3], "expected": "Fizz"},
                {"function": "fizzbuzz", "input": [5], "expected": "Buzz"},
                {"function": "fizzbuzz", "input": [15], "expected": "FizzBuzz"},
                {"function": "fizzbuzz", "input": [7], "expected": "7"},
            ],
        ))
        suite.add_task(CodeGenerationTask(
            "code_reverse",
            "Write a Python function reverse_words(s) that reverses the order of words "
            "in a string. Example: 'hello world' -> 'world hello'",
            test_cases=[
                {"function": "reverse_words", "input": ["hello world"], "expected": "world hello"},
                {"function": "reverse_words", "input": ["a b c"], "expected": "c b a"},
                {"function": "reverse_words", "input": ["single"], "expected": "single"},
            ],
        ))
        suite.add_task(PlanningTask(
            "plan_deploy",
            "Deploy a web application to production with zero downtime.",
            constraints=["Must have rollback capability", "Must run health checks"],
            expected_steps=5,
        ))

        return suite

    def _build_summary(self, elapsed: float, final_baseline: EvalResult) -> SimSummary:
        """Build the final simulation summary."""
        accepted = [c for c in self._cycle_history if c.accepted]
        rejected = [c for c in self._cycle_history if not c.accepted]

        mutation_stats: dict[str, dict] = {}
        for c in self._cycle_history:
            mt = c.mutation_type
            if mt not in mutation_stats:
                mutation_stats[mt] = {"attempted": 0, "accepted": 0, "total_improvement": 0.0}
            mutation_stats[mt]["attempted"] += 1
            if c.accepted:
                mutation_stats[mt]["accepted"] += 1
                mutation_stats[mt]["total_improvement"] += c.raw_improvement

        initial_score = self._cycle_history[0].baseline_score if self._cycle_history else 0.0

        thought_log = [
            {
                "cycle": c.cycle_num,
                "mutation_type": c.mutation_type,
                "accepted": c.accepted,
                "delta": round(c.raw_improvement, 4),
                "thought": c.thought,
            }
            for c in self._cycle_history if c.thought
        ]

        return SimSummary(
            total_cycles=len(self._cycle_history),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            initial_score=initial_score,
            final_score=final_baseline.aggregate_score,
            total_improvement=final_baseline.aggregate_score - initial_score,
            best_composite_score=max((c.composite_score for c in accepted), default=0.0),
            mutation_stats=mutation_stats,
            dag_depth=self.dag.max_depth,
            reputation=self.reputation.get_reputation(
                self._agent.agent_id if self._agent else ""
            ),
            elapsed_s=elapsed,
            cycles=self._cycle_history,
            thought_log=thought_log,
            self_portrait_svg=self._self_portrait_svg,
        )
