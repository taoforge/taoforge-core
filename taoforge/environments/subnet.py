"""SubnetEnvironment — Bittensor subnet metagraph as an open-ended environment.

The agent receives a snapshot of a subnet's metagraph (validators, miners, stake,
incentives, weights) and explores it freely. No prescribed analysis tasks.
Scored only on factual grounding: are UIDs real? are numbers accurate?
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from taoforge.environments.base import Environment, EnvironmentContext, GroundingResult
from taoforge.subnets.data import MetagraphFetcher, MetagraphSnapshot
from taoforge.subnets.scorers import score_accuracy, score_depth, score_specificity

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SubnetEnvironment(Environment):
    """Bittensor subnet metagraph environment.

    Provides metagraph data to agents and verifies that their output
    references real UIDs, accurate stake/incentive values, and
    identifies genuine structural patterns.

    Usage:
        fetcher = MetagraphFetcher()
        snapshot = fetcher.fetch(netuid=1)
        env = SubnetEnvironment(snapshot)
        context = env.get_context()   # pass context.raw_data to agent
        result = env.verify_grounding(agent_output)
    """

    def __init__(
        self,
        snapshot: MetagraphSnapshot,
        specificity_weight: float = 0.35,
        accuracy_weight: float = 0.35,
        depth_weight: float = 0.30,
    ) -> None:
        self._snapshot = snapshot
        self._spec_w = specificity_weight
        self._acc_w = accuracy_weight
        self._dep_w = depth_weight

    @classmethod
    def from_netuid(
        cls,
        netuid: int,
        network: str = "finney",
        fetcher: MetagraphFetcher | None = None,
        **kwargs,
    ) -> "SubnetEnvironment":
        """Convenience constructor — fetch snapshot by netuid."""
        f = fetcher or MetagraphFetcher()
        snapshot = f.fetch(netuid=netuid, network=network)
        return cls(snapshot, **kwargs)

    @property
    def domain(self) -> str:
        return f"bittensor_subnet_{self._snapshot.netuid}"

    @property
    def snapshot(self) -> MetagraphSnapshot:
        return self._snapshot

    def get_context(self) -> EnvironmentContext:
        """Build agent-facing context from the metagraph snapshot."""
        raw_data = self._snapshot.to_prompt_summary(max_neurons=20)
        structured_data = self._snapshot.to_dict()

        return EnvironmentContext(
            domain=self.domain,
            raw_data=raw_data,
            structured_data=structured_data,
            metadata={
                "netuid": self._snapshot.netuid,
                "network": self._snapshot.network,
                "block": self._snapshot.block,
                "neuron_count": len(self._snapshot.neurons),
                "validator_count": self._snapshot.validator_count,
                "miner_count": self._snapshot.miner_count,
            },
        )

    def verify_grounding(self, output: str) -> GroundingResult:
        """Verify agent output against the metagraph.

        Checks three independent axes:
        - Specificity: does the agent cite real UIDs / hotkeys?
        - Accuracy:    are numerical claims (stake, emission) correct?
        - Depth:       does the output identify non-obvious patterns?

        Returns a composite score and per-axis breakdown.
        """
        spec = score_specificity(output, self._snapshot)
        acc = score_accuracy(output, self._snapshot)
        dep = score_depth(output, self._snapshot)

        composite = (
            self._spec_w * spec.score
            + self._acc_w * acc.score
            + self._dep_w * dep.score
        )

        verified_claims = (
            spec.details.get("verified_refs", 0)
            + acc.details.get("accurate_claims", 0)
        )
        total_claims = (
            spec.details.get("total_refs", 0)
            + acc.details.get("total_claims", 0)
        )

        logger.debug(
            f"Grounding [{self.domain}]: "
            f"spec={spec.score:.3f} acc={acc.score:.3f} dep={dep.score:.3f} "
            f"-> composite={composite:.3f}"
        )

        return GroundingResult(
            score=composite,
            verified_claims=verified_claims,
            total_claims=total_claims,
            details={
                "specificity": round(spec.score, 4),
                "accuracy": round(acc.score, 4),
                "depth": round(dep.score, 4),
                "specificity_details": spec.details,
                "accuracy_details": acc.details,
                "depth_details": dep.details,
            },
        )
