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
        "prompt_chain_refactor": 0.30,
        "inference_pipeline": 0.25,
        "tool_graph_rewire": 0.15,
        "lora_merge": 0.10,
        "memory_index_rebuild": 0.05,
        "subnet_switch": 0.15,
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
        # Subnet analysis context — populated after each eval for grounded thoughts
        self._last_analysis_preview: str = ""
        self._last_data_summary: str = ""
        self._last_phase_scores: dict[str, float] = {}
        self._current_netuid: int = 1  # will be set from evaluator profile if available
        self._subnet_history: list[dict] = []

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

        # Handle subnet switch: swap evaluator rather than mutating agent config
        if mutation_type == MutationType.SUBNET_SWITCH:
            return self._run_subnet_switch_cycle(cycle_num, current_baseline, delta, cycle_start)

        # 2. Save agent state (for rollback)
        pre_state_hash = self._agent.get_state_hash()
        pre_config = copy.deepcopy(self._agent.config)

        # 3. Apply mutation
        self.mutator.apply_mutation(self._agent, delta)

        # 4. Evaluate mutated agent
        delta_result = self._eval(self._agent)
        self._extract_eval_context(delta_result)
        phase_scores_snapshot = dict(self._last_phase_scores)  # snapshot before next cycle overwrites

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
            phase_scores=phase_scores_snapshot,
            netuid=self._current_netuid,
        )

    def _run_subnet_switch_cycle(
        self,
        cycle_num: int,
        current_baseline: "EvalResult",
        delta: "MutationDelta",
        cycle_start: float,
    ) -> "CycleResult":
        """Handle a subnet_switch mutation — swap evaluator, eval, accept/reject."""
        from taoforge.subnets.analysis_adapter import SubnetAnalysisAdapter
        from taoforge.subnets.registry import SubnetRegistry, SubnetProfile, SubnetDomain
        from taoforge.mutation.types import MutationType

        target_netuid = delta.parameters.get("target_netuid", 1)
        old_evaluator = self._evaluator
        old_netuid = self._current_netuid

        # Build adapter for target subnet
        registry = SubnetRegistry()
        profile = registry.get(target_netuid) or SubnetProfile(
            netuid=target_netuid,
            name=f"SN{target_netuid}",
            domain=SubnetDomain.DATA,
            benchmark_type="subnet_analysis",
        )
        new_adapter = SubnetAnalysisAdapter(profile)
        self._evaluator = new_adapter.evaluate_locally

        # Evaluate on new subnet — reject gracefully if snapshot unavailable
        try:
            delta_result = self._eval(self._agent)
        except (FileNotFoundError, Exception) as e:
            logger.warning(f"Subnet switch to SN{target_netuid} failed: {e}. Rejecting.")
            self._evaluator = old_evaluator
            cycle_time = time.monotonic() - cycle_start
            return CycleResult(
                cycle_num=cycle_num,
                mutation_type=MutationType.SUBNET_SWITCH.value,
                mutation_description=f"Switch to SN{target_netuid} failed: no data available",
                baseline_score=current_baseline.aggregate_score,
                delta_score=current_baseline.aggregate_score,
                raw_improvement=0.0,
                composite_score=0.0,
                accepted=False,
                cycle_time_s=cycle_time,
                netuid=old_netuid,
            )
        self._extract_eval_context(delta_result)

        raw_improvement = delta_result.aggregate_score - current_baseline.aggregate_score

        # Build proposal for scoring
        proposal = ImprovementProposal(
            agent_id=self._agent.agent_id,
            mutation_type=MutationType.SUBNET_SWITCH.value,
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
            parent_delta=self._proposal_history[-1].proposal_id if self._proposal_history else None,
        )

        holdout_result = self._eval(self._agent)
        score_vector = ScoreVector.from_results(current_baseline, delta_result)
        composite_score = compute_score(
            proposal=proposal,
            baseline_result=current_baseline,
            delta_result=delta_result,
            weights=self.config.scoring_weights,
            dag=self.dag,
            holdout_result=holdout_result,
            proposal_history=self._proposal_history,
        )

        accepted = raw_improvement > 0 and composite_score > 0.01

        if accepted:
            self._current_netuid = target_netuid
            self._subnet_history.append({
                "netuid": target_netuid,
                "cycle": cycle_num,
                "score": round(delta_result.aggregate_score, 4),
                "reason": delta.parameters.get("reason", ""),
            })
            from taoforge.registry.node import DAGNode
            node = DAGNode(
                node_id=proposal.proposal_id,
                agent_id=self._agent.agent_id,
                parent_id=proposal.parent_delta,
                mutation_type=MutationType.SUBNET_SWITCH.value,
                improvement_delta=raw_improvement,
                benchmark_id=self._suite.suite_id,
                proof_hash=hash_score(delta_result.aggregate_score),
                reputation_at_time=self.reputation.get_reputation(self._agent.agent_id),
            )
            self.dag.add_node(node)
            self.reputation.update(self._agent.agent_id, raw_improvement)
            self._proposal_history.append(proposal)
        else:
            # Restore old evaluator — don't switch
            self._evaluator = old_evaluator

        thought = self._generate_thought(
            cycle_num=cycle_num,
            mutation_type=MutationType.SUBNET_SWITCH.value,
            mutation_description=delta.description,
            baseline_score=current_baseline.aggregate_score,
            delta_score=delta_result.aggregate_score,
            raw_improvement=raw_improvement,
        )

        cycle_time = time.monotonic() - cycle_start
        return CycleResult(
            cycle_num=cycle_num,
            mutation_type=MutationType.SUBNET_SWITCH.value,
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

    def _extract_eval_context(self, result: EvalResult) -> None:
        """Pull analysis preview, raw data summary, and phase scores from eval result."""
        for ts in result.task_scores:
            self._last_phase_scores[ts.task_id] = ts.score
            if ts.task_id == "open_ended_analysis":
                preview = ts.metadata.get("output_preview", "")
                if preview:
                    self._last_analysis_preview = preview
                data_summary = ts.metadata.get("data_summary", "")
                if data_summary:
                    self._last_data_summary = data_summary

    def _select_mutation(self) -> MutationType:
        """Select a mutation type, biased by the weakest phase from the last eval cycle."""
        import random
        type_map = {
            "prompt_chain_refactor": MutationType.PROMPT_CHAIN_REFACTOR,
            "inference_pipeline": MutationType.INFERENCE_PIPELINE,
            "tool_graph_rewire": MutationType.TOOL_GRAPH_REWIRE,
            "lora_merge": MutationType.LORA_MERGE,
            "memory_index_rebuild": MutationType.MEMORY_INDEX_REBUILD,
            "subnet_switch": MutationType.SUBNET_SWITCH,
        }

        # Start with configured base weights
        weights = dict(self.config.mutation_weights)

        # Bias toward mutations that address the weakest eval phase
        if self._last_phase_scores:
            analysis_score = self._last_phase_scores.get("open_ended_analysis", 0.5)
            self_eval_score = self._last_phase_scores.get("self_evaluation", 0.5)
            evolution_score = self._last_phase_scores.get("criteria_evolution", 0.5)

            min_score = min(analysis_score, self_eval_score, evolution_score)
            if min_score == analysis_score and analysis_score < 0.4:
                # Weak grounding → try a different prompting approach
                weights["prompt_chain_refactor"] = weights.get("prompt_chain_refactor", 0.35) * 2.0
            elif min_score == self_eval_score and self_eval_score < 0.4:
                # Poor self-calibration → tune temperature/sampling
                weights["inference_pipeline"] = weights.get("inference_pipeline", 0.30) * 2.0
            elif min_score == evolution_score and evolution_score < 0.4:
                # Weak criteria-following → rewire prompt/tool structure
                weights["tool_graph_rewire"] = weights.get("tool_graph_rewire", 0.15) * 2.5

            # If we've been stuck for 2+ cycles and have a subnet evaluator, strongly bias toward switching
            if self._plateau_counter >= 2 and self._evaluator is not None:
                weights["subnet_switch"] = weights.get("subnet_switch", 0.15) * (1 + self._plateau_counter)

        names = list(weights.keys())
        wvals = [weights[n] for n in names]
        chosen = random.choices(names, weights=wvals)[0]
        return type_map.get(chosen, MutationType.PROMPT_CHAIN_REFACTOR)

    def _create_mutation(self, mutation_type: MutationType) -> MutationDelta:
        """Create a concrete mutation delta."""
        import random

        if mutation_type == MutationType.PROMPT_CHAIN_REFACTOR:
            # Use subnet-analysis-specific prompts if we're running a subnet eval
            if self._last_analysis_preview:
                prompts = [
                    "You are a meticulous blockchain data analyst. When analyzing subnet data, always cite specific UID numbers, their exact stake values, and calculate concentration ratios. Your strength is in spotting statistical anomalies.",
                    "You are an expert in distributed consensus systems. Focus your analysis on validator-miner dynamics, weight distributions, and trust relationships. Always quantify patterns numerically.",
                    "You are a rigorous financial analyst specializing in tokenomics. For each subnet, compute stake concentration (Gini coefficient), identify top holders, and assess emission efficiency. Be exact with numbers.",
                    "You are a network topology expert. When analyzing metagraphs, examine the weight matrix structure, identify clusters, and quantify how stake concentration affects miner incentives. Show your math.",
                    "You are a systematic data scientist. Structure your subnet analysis as: (1) summary statistics, (2) distribution analysis, (3) outlier detection, (4) pattern identification. Reference exact values.",
                    "You are a careful empiricist. For subnet analysis, ground every claim in the data: cite the UID, its stake, its rank, its emission. Avoid generalizations — be specific and verifiable.",
                    "You are a strategic analyst. Assess subnets through the lens of competitive dynamics: who controls majority stake, which miners receive the most incentive, and what structural advantages or vulnerabilities exist.",
                    "You are a quantitative researcher. Transform raw metagraph data into insight: compute validator concentration, miner efficiency ratios, and trust network density. Every observation must be backed by numbers.",
                ]
            else:
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
                description="System prompt variation",
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

        elif mutation_type == MutationType.SUBNET_SWITCH:
            from taoforge.subnets.registry import SubnetRegistry
            from taoforge.subnets.data import _SNAPSHOTS_DIR
            registry = SubnetRegistry()
            all_subnets = registry.get_all()
            # Only offer subnets that have a cached snapshot available
            def _has_snapshot(netuid: int) -> bool:
                return bool(list(_SNAPSHOTS_DIR.glob(f"sn{netuid}_*.json")))
            other_subnets = [
                s for s in all_subnets
                if s.netuid != self._current_netuid and s.netuid != 0 and _has_snapshot(s.netuid)
            ]
            # If no other subnets have snapshots, fall back to any registered subnet
            if not other_subnets:
                other_subnets = [s for s in all_subnets if s.netuid != self._current_netuid and s.netuid != 0]

            name = getattr(self._agent.config, "name", None) or self._agent.agent_id[:8] if self._agent else "agent"
            current_name = registry.get(self._current_netuid)
            current_subnet_name = current_name.name if current_name else f"SN{self._current_netuid}"
            subnet_list = "\n".join(
                f"  SN{s.netuid} ({s.name}): {s.description}"
                for s in sorted(other_subnets, key=lambda x: x.netuid)
            )
            history_str = ""
            if self._subnet_history:
                history_str = "\nSubnets you have already visited:\n" + "\n".join(
                    f"  SN{h['netuid']}: score {h['score']:.4f} at cycle {h['cycle']}"
                    for h in self._subnet_history
                ) + "\n"

            prompt = (
                f"You are {name}, an autonomous agent on Bittensor.\n"
                f"You have been analyzing SN{self._current_netuid} ({current_subnet_name}) "
                f"for several cycles with no improvement.\n"
                f"Current score: {self._best_score:.4f}\n"
                f"{history_str}\n"
                f"Available subnets to explore:\n{subnet_list}\n\n"
                f"Which subnet should you analyze next to maximize your improvement potential?\n"
                f"Consider: your current analysis strengths, which subnets have rich validator-miner data, "
                f"and where your approach is most likely to score well.\n\n"
                f"Respond with ONLY a JSON object, nothing else:\n"
                f"{{\"netuid\": <number>, \"reason\": \"<one sentence why>\"}}"
            )

            target_netuid = None
            reason = ""
            if self._agent:
                try:
                    result = self._agent.generate(prompt)
                    if result and result.text:
                        import json as _json
                        import re as _re
                        text = result.text.strip()
                        m = _re.search(r'\{[^}]+\}', text)
                        if m:
                            parsed = _json.loads(m.group())
                            target_netuid = int(parsed.get("netuid", 0))
                            reason = parsed.get("reason", "")
                except Exception:
                    pass

            # Fallback: pick the subnet the agent hasn't tried yet with the most neurons
            if not target_netuid or target_netuid == self._current_netuid:
                visited = {h["netuid"] for h in self._subnet_history} | {self._current_netuid}
                unvisited = [s for s in other_subnets if s.netuid not in visited]
                chosen = random.choice(unvisited) if unvisited else random.choice(other_subnets)
                target_netuid = chosen.netuid
                reason = f"Exploring {chosen.name} as next unvisited subnet"

            return MutationDelta(
                mutation_type=mutation_type,
                description=f"Switch to SN{target_netuid}: {reason}",
                parameters={"target_netuid": target_netuid, "reason": reason},
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
        """Ask the agent to narrate its reasoning, grounded in what it actually observed."""
        if self._agent is None:
            return ""
        try:
            name = getattr(self._agent.config, "name", None) or self._agent.agent_id[:8]
            recent = self._cycle_history[-3:] if self._cycle_history else []
            history_str = "\n".join(
                f"  Cycle {c.cycle_num}: {c.mutation_type} {'✓ accepted' if c.accepted else '✗ rejected'} "
                f"(score {c.baseline_score:.4f} → {c.delta_score:.4f}, {c.raw_improvement:+.4f})"
                for c in recent
            ) or "  none yet"

            outcome = "improved" if raw_improvement > 0 else "did not improve"

            # Raw subnet data gives the agent concrete numbers to reference
            data_block = ""
            if self._last_data_summary:
                data_block = (
                    f"SUBNET DATA YOU ANALYZED THIS CYCLE:\n"
                    f"{self._last_data_summary}\n\n"
                )

            # Phase scores tell the agent which dimensions it's struggling with
            phase_block = ""
            if self._last_phase_scores:
                phase_lines = "\n".join(
                    f"  {k.replace('_', ' ')}: {v:.3f}"
                    for k, v in self._last_phase_scores.items()
                )
                phase_block = f"EVAL PHASE SCORES THIS CYCLE:\n{phase_lines}\n\n"

            prompt = (
                f"You are {name}, an autonomous agent on the Bittensor network.\n"
                f"Your task: analyze Bittensor subnet metagraph data and improve your "
                f"analysis quality each cycle through self-mutation.\n\n"
                f"{data_block}"
                f"{phase_block}"
                f"CYCLE {cycle_num} OUTCOME:\n"
                f"  Mutation applied: {mutation_type} ({mutation_description})\n"
                f"  Score: {baseline_score:.4f} → {delta_score:.4f} "
                f"({outcome}, {raw_improvement:+.4f})\n\n"
                f"RECENT HISTORY:\n{history_str}\n\n"
                f"Write 3-4 sentences as yourself, in first person. You MUST:\n"
                f"1. Reference at least one specific data point from the subnet above "
                f"(e.g. a UID number, a stake value, a Gini coefficient, a validator count)\n"
                f"2. Explain what that observation tells you about this subnet's structure\n"
                f"3. Connect it to why this cycle's mutation {'helped' if raw_improvement > 0 else 'did not help'}\n"
                f"4. State your hypothesis for what to try next\n\n"
                f"Do NOT speak generically about 'mutations' or 'performance'. "
                f"Speak about the actual subnet data. No preamble, no hedging."
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

        peak_score = max((c.delta_score for c in self._cycle_history), default=0.0)
        peak_cycle = next(
            (c.cycle_num for c in self._cycle_history if c.delta_score == peak_score), 0
        )

        thought_log = [
            {
                "cycle": c.cycle_num,
                "mutation_type": c.mutation_type,
                "mutation_description": c.mutation_description,
                "accepted": c.accepted,
                "baseline_score": round(c.baseline_score, 4),
                "delta_score": round(c.delta_score, 4),
                "delta": round(c.raw_improvement, 4),
                "composite_score": round(c.composite_score, 4),
                "holdout_score": round(c.holdout_score, 4),
                "cycle_time_s": round(c.cycle_time_s, 2),
                "phase_scores": {k: round(v, 4) for k, v in c.phase_scores.items()},
                "netuid": c.netuid,
                "thought": c.thought,
            }
            for c in self._cycle_history
        ]

        return SimSummary(
            total_cycles=len(self._cycle_history),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            initial_score=initial_score,
            final_score=final_baseline.aggregate_score,
            peak_score=peak_score,
            peak_cycle=peak_cycle,
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
            netuid=self._current_netuid,
            subnet_history=self._subnet_history,
        )
