"""Subnet targeting strategy — how agents select and specialize on subnets."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from taoforge.subnets.registry import SubnetDomain, SubnetProfile, SubnetRegistry

logger = logging.getLogger(__name__)


@dataclass
class SubnetTarget:
    """An agent's active target subnet with progress tracking."""

    profile: SubnetProfile
    mode: str = "observer"  # "competitor" | "observer" | "offline"
    priority: float = 1.0  # Higher = more focus
    current_score: float = 0.0  # Agent's current eval score on this subnet
    best_score: float = 0.0
    improvement_count: int = 0
    mutations_tried: int = 0
    last_attempt_timestamp: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.mutations_tried == 0:
            return 0.0
        return self.improvement_count / self.mutations_tried

    @property
    def netuid(self) -> int:
        return self.profile.netuid


class TargetingStrategy:
    """Manages which subnets an agent targets and how it allocates effort.

    Agents specialize in 1-3 subnets based on:
    - Domain affinity (what model/capability type the agent has)
    - Reward signal (which subnets offer best ROI)
    - Competition level (avoid overcrowded subnets)
    - Historical success (double down on what works)
    """

    def __init__(
        self,
        registry: SubnetRegistry,
        max_targets: int = 3,
    ) -> None:
        self.registry = registry
        self.max_targets = max_targets
        self._targets: dict[int, SubnetTarget] = {}

    def add_target(
        self,
        netuid: int,
        mode: str = "observer",
        priority: float = 1.0,
    ) -> Optional[SubnetTarget]:
        """Add a subnet as a target."""
        if len(self._targets) >= self.max_targets:
            logger.warning(
                f"Max targets ({self.max_targets}) reached. "
                f"Remove a target before adding netuid={netuid}."
            )
            return None

        profile = self.registry.get(netuid)
        if profile is None:
            logger.warning(f"Unknown subnet netuid={netuid}")
            return None

        target = SubnetTarget(profile=profile, mode=mode, priority=priority)
        self._targets[netuid] = target
        logger.info(
            f"Target added | netuid={netuid} | name={profile.name} | "
            f"mode={mode} | priority={priority}"
        )
        return target

    def remove_target(self, netuid: int) -> bool:
        if netuid in self._targets:
            del self._targets[netuid]
            return True
        return False

    def get_targets(self) -> list[SubnetTarget]:
        """Get active targets sorted by priority (highest first)."""
        return sorted(self._targets.values(), key=lambda t: t.priority, reverse=True)

    def get_target(self, netuid: int) -> Optional[SubnetTarget]:
        return self._targets.get(netuid)

    def select_next_target(self) -> Optional[SubnetTarget]:
        """Select the next subnet to attempt improvement on.

        Uses a weighted selection based on priority, success rate, and
        time since last attempt.
        """
        targets = self.get_targets()
        if not targets:
            return None

        # Simple priority-based selection for now
        # TODO: Implement more sophisticated selection (UCB, Thompson sampling)
        return targets[0]

    def record_attempt(self, netuid: int, improved: bool, score: float = 0.0) -> None:
        """Record an improvement attempt result."""
        target = self._targets.get(netuid)
        if target is None:
            return

        target.mutations_tried += 1
        if improved:
            target.improvement_count += 1
        if score > target.best_score:
            target.best_score = score
        target.current_score = score

        import time
        target.last_attempt_timestamp = time.time()

    def auto_select_targets(
        self,
        agent_domain: SubnetDomain | None = None,
        prefer_easy: bool = True,
    ) -> list[SubnetTarget]:
        """Automatically select the best subnets to target.

        Args:
            agent_domain: If set, prefer subnets in this domain.
            prefer_easy: If True, prefer less competitive subnets.

        Returns:
            List of selected targets.
        """
        candidates = self.registry.get_all()

        # Filter by domain if specified
        if agent_domain:
            domain_matches = [s for s in candidates if s.domain == agent_domain]
            if domain_matches:
                candidates = domain_matches

        # Sort by attractiveness
        if prefer_easy:
            candidates.sort(key=lambda s: s.difficulty_estimate)
        else:
            candidates.sort(key=lambda s: s.avg_incentive, reverse=True)

        # Take top N
        for profile in candidates[: self.max_targets]:
            self.add_target(profile.netuid, mode="observer")

        return self.get_targets()

    @property
    def num_targets(self) -> int:
        return len(self._targets)
