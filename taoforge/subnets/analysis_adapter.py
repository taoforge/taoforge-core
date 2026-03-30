"""Subnet analysis adapter — plugs open-ended analysis into the eval framework.

Uses EnvironmentHarness (open-ended, no prescribed objectives) instead of
the old three-task prescribed suite. Agents receive raw metagraph data and
decide what to investigate. Scored only on factual grounding.
"""

from __future__ import annotations

import logging
from typing import Any

from taoforge.environments.harness import EnvironmentHarness
from taoforge.environments.subnet import SubnetEnvironment
from taoforge.evaluation.results import EvalResult
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.subnets.adapter import SubnetAdapter
from taoforge.subnets.data import MetagraphFetcher, MetagraphSnapshot
from taoforge.subnets.registry import SubnetProfile

logger = logging.getLogger(__name__)


class SubnetAnalysisAdapter(SubnetAdapter):
    """Adapter for open-ended subnet analysis via EnvironmentHarness.

    Agents receive raw metagraph data with a single open-ended prompt.
    They decide what questions to ask and what to investigate.
    Scored on whether their claims are factually grounded in the data.

    Replaces the old prescribed three-task suite (SubnetAnalysisTask +
    SelfEvaluationTask + CriteriaEvolutionTask) with the same three-phase
    structure but open-ended prompts.
    """

    def __init__(
        self,
        profile: SubnetProfile,
        snapshot: MetagraphSnapshot | None = None,
        fetcher: MetagraphFetcher | None = None,
    ) -> None:
        super().__init__(profile)
        self._snapshot = snapshot
        self._fetcher = fetcher or MetagraphFetcher()
        self._harness = EnvironmentHarness()

    def _get_environment(self) -> SubnetEnvironment:
        """Get or create the SubnetEnvironment, fetching snapshot if needed."""
        if self._snapshot is None:
            self._snapshot = self._fetcher.fetch(
                netuid=self.profile.netuid,
                network="finney",
            )
        return SubnetEnvironment(self._snapshot)

    def build_benchmark_suite(self) -> BenchmarkSuite:
        """Returns a minimal stub suite for framework compatibility.

        The real evaluation happens in evaluate_locally() via EnvironmentHarness.
        BenchmarkSuite is not used for open-ended evaluation.
        """
        return BenchmarkSuite(
            suite_id=f"open_ended_sn{self.profile.netuid}",
            version="0.2",
        )

    def evaluate_on_subnet(self, agent: Any) -> EvalResult:
        # Open-ended analysis is inherently local — we analyze data, not compete on-chain
        return self.evaluate_locally(agent)

    def evaluate_locally(self, agent: Any) -> EvalResult:
        """Run the open-ended eval cycle via EnvironmentHarness."""
        environment = self._get_environment()
        return self._harness.run(agent, environment)

    def _suggest_mutations(self, weak_areas: list[str]) -> list[str]:
        """Suggest mutations based on which phases scored lowest."""
        suggestions = []
        for area in weak_areas:
            if "analysis" in area or "grounding" in area:
                # Low grounding → try refining the agent's prompting approach
                suggestions.append("prompt_chain_refactor")
            elif "self_eval" in area or "calibration" in area:
                # Poor self-calibration → try tuning inference params
                suggestions.append("inference_pipeline")
            elif "evolution" in area or "criteria" in area:
                # Low criteria-following → try prompt or tool graph changes
                suggestions.append("tool_graph_rewire")

        return suggestions or ["prompt_chain_refactor", "inference_pipeline"]
