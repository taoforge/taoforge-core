"""Autonomous agent loop — the core self-improvement cycle targeting subnets."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from taoforge.evaluation.results import EvalResult
from taoforge.mutation.applicator import MutationApplicator
from taoforge.mutation.types import AgentState, MutationDelta, MutationType
from taoforge.subnets.adapter import SubnetAdapter, create_adapter
from taoforge.subnets.targeting import SubnetTarget, TargetingStrategy

logger = logging.getLogger(__name__)


@dataclass
class ImprovementAttempt:
    """Record of one self-improvement attempt."""

    target_netuid: int
    mutation_type: str
    baseline_score: float
    delta_score: float
    improved: bool
    timestamp: float
    duration_seconds: float


class AutonomousAgentLoop:
    """The autonomous self-improvement loop.

    Each cycle:
    1. Select a target subnet (via TargetingStrategy)
    2. Run baseline eval (via SubnetAdapter)
    3. Select and apply a mutation
    4. Run delta eval
    5. If improved, submit proposal
    6. Record result, update strategy
    """

    def __init__(
        self,
        strategy: TargetingStrategy,
        applicator: MutationApplicator | None = None,
        agent_state: AgentState | None = None,
    ) -> None:
        self.strategy = strategy
        self.applicator = applicator or MutationApplicator()
        self.agent_state = agent_state or AgentState()
        self._adapters: dict[int, SubnetAdapter] = {}
        self._history: list[ImprovementAttempt] = []

    def get_adapter(self, target: SubnetTarget) -> SubnetAdapter:
        """Get or create an adapter for a target subnet."""
        if target.netuid not in self._adapters:
            self._adapters[target.netuid] = create_adapter(target.profile)
        return self._adapters[target.netuid]

    def run_cycle(self, agent: Any = None) -> Optional[ImprovementAttempt]:
        """Run one autonomous improvement cycle.

        Args:
            agent: The agent to evaluate (if None, uses self.agent_state).

        Returns:
            ImprovementAttempt record, or None if no target available.
        """
        # 1. Select target
        target = self.strategy.select_next_target()
        if target is None:
            logger.warning("No targets available — skipping cycle.")
            return None

        adapter = self.get_adapter(target)
        start = time.time()

        logger.info(
            f"Starting improvement cycle | subnet={target.profile.name} "
            f"(netuid={target.netuid}) | mode={target.mode}"
        )

        # 2. Baseline eval
        if target.mode == "competitor":
            baseline_result = adapter.evaluate_on_subnet(agent)
        else:
            baseline_result = adapter.evaluate_locally(agent)

        # 3. Analyze opportunities and select mutation
        opportunity = adapter.get_improvement_opportunity(baseline_result)
        mutation_type = self._select_mutation(opportunity, target)

        # 4. Apply mutation
        delta = MutationDelta(
            mutation_type=mutation_type,
            description=f"Auto-mutation for subnet {target.netuid}: {mutation_type.value}",
        )

        try:
            new_state = self.applicator.apply(self.agent_state, delta)
        except Exception as e:
            logger.error(f"Mutation failed: {e}")
            return None

        # 5. Delta eval
        if target.mode == "competitor":
            delta_result = adapter.evaluate_on_subnet(agent)
        else:
            delta_result = adapter.evaluate_locally(agent)

        # 6. Compare
        improved = delta_result.aggregate_score > baseline_result.aggregate_score
        duration = time.time() - start

        attempt = ImprovementAttempt(
            target_netuid=target.netuid,
            mutation_type=mutation_type.value,
            baseline_score=baseline_result.aggregate_score,
            delta_score=delta_result.aggregate_score,
            improved=improved,
            timestamp=time.time(),
            duration_seconds=duration,
        )

        # 7. Record and update strategy
        self._history.append(attempt)
        self.strategy.record_attempt(
            netuid=target.netuid,
            improved=improved,
            score=delta_result.aggregate_score,
        )

        if improved:
            self.agent_state = new_state
            logger.info(
                f"IMPROVEMENT | subnet={target.profile.name} | "
                f"{baseline_result.aggregate_score:.4f} -> {delta_result.aggregate_score:.4f} | "
                f"mutation={mutation_type.value}"
            )
        else:
            logger.info(
                f"No improvement | subnet={target.profile.name} | "
                f"mutation={mutation_type.value} | "
                f"baseline={baseline_result.aggregate_score:.4f} "
                f"delta={delta_result.aggregate_score:.4f}"
            )

        return attempt

    def run(self, max_cycles: int = 100, cooldown: float = 5.0) -> list[ImprovementAttempt]:
        """Run the autonomous loop for multiple cycles.

        Args:
            max_cycles: Maximum number of improvement cycles.
            cooldown: Seconds between cycles.

        Returns:
            List of all improvement attempts.
        """
        logger.info(f"Starting autonomous agent loop | max_cycles={max_cycles}")

        for i in range(max_cycles):
            attempt = self.run_cycle()
            if attempt is None:
                break
            time.sleep(cooldown)

        improvements = sum(1 for a in self._history if a.improved)
        logger.info(
            f"Agent loop complete | cycles={len(self._history)} | "
            f"improvements={improvements} | "
            f"success_rate={improvements/max(len(self._history),1):.1%}"
        )
        return self._history

    def _select_mutation(
        self,
        opportunity: dict,
        target: SubnetTarget,
    ) -> MutationType:
        """Select the best mutation type for the current opportunity."""
        suggested = opportunity.get("suggested_mutations", [])

        # Map suggestion strings to MutationType
        type_map = {
            "lora_merge": MutationType.LORA_MERGE,
            "tool_graph_rewire": MutationType.TOOL_GRAPH_REWIRE,
            "prompt_chain_refactor": MutationType.PROMPT_CHAIN_REFACTOR,
            "memory_index_rebuild": MutationType.MEMORY_INDEX_REBUILD,
            "inference_pipeline": MutationType.INFERENCE_PIPELINE,
        }

        for s in suggested:
            if s in type_map:
                return type_map[s]

        # Default: prompt chain refactor (safest, most broadly applicable)
        return MutationType.PROMPT_CHAIN_REFACTOR

    @property
    def history(self) -> list[ImprovementAttempt]:
        return list(self._history)

    @property
    def total_improvements(self) -> int:
        return sum(1 for a in self._history if a.improved)
