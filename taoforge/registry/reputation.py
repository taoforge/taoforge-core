"""Reputation system — tracks agent reputation with decay and streak multipliers."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class ReputationRecord:
    """Reputation state for a single agent."""

    agent_id: str
    score: float = 0.0
    total_improvements: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_improvement_at: float = 0.0
    last_decay_at: float = field(default_factory=time.time)


class ReputationSystem:
    """Agent reputation with decay mechanics and streak multipliers.

    Reputation decays over time — continuous improvement required to
    maintain score. Longer verified improvement streaks earn a multiplier.
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        decay_interval_hours: float = 24.0,
        streak_multiplier: float = 0.1,
    ) -> None:
        self.decay_rate = decay_rate
        self.decay_interval = decay_interval_hours * 3600
        self.streak_multiplier = streak_multiplier
        self._records: dict[str, ReputationRecord] = {}

    def get_reputation(self, agent_id: str) -> float:
        """Get current reputation for an agent (after decay)."""
        record = self._records.get(agent_id)
        if record is None:
            return 0.0

        self._apply_decay(record)
        return record.score

    def update(self, agent_id: str, verified_improvement: float) -> float:
        """Update reputation after a verified improvement.

        Args:
            agent_id: The agent's hotkey.
            verified_improvement: Magnitude of verified improvement.

        Returns:
            New reputation score.
        """
        record = self._records.get(agent_id)
        if record is None:
            record = ReputationRecord(agent_id=agent_id)
            self._records[agent_id] = record

        self._apply_decay(record)

        # Update streak
        record.current_streak += 1
        record.longest_streak = max(record.longest_streak, record.current_streak)

        # Streak multiplier
        multiplier = 1.0 + self.streak_multiplier * min(record.current_streak, 10)

        # Add improvement to reputation
        record.score += verified_improvement * multiplier
        record.total_improvements += 1
        record.last_improvement_at = time.time()

        return record.score

    def break_streak(self, agent_id: str) -> None:
        """Break an agent's improvement streak (failed or rejected proposal)."""
        record = self._records.get(agent_id)
        if record:
            record.current_streak = 0

    def _apply_decay(self, record: ReputationRecord) -> None:
        """Apply time-based reputation decay."""
        now = time.time()
        elapsed = now - record.last_decay_at

        if elapsed >= self.decay_interval:
            periods = elapsed / self.decay_interval
            decay_factor = math.exp(-self.decay_rate * periods)
            record.score *= decay_factor
            record.last_decay_at = now

    def get_record(self, agent_id: str) -> ReputationRecord | None:
        return self._records.get(agent_id)

    def get_leaderboard(self, top_n: int = 10) -> list[ReputationRecord]:
        """Get top agents by reputation."""
        for record in self._records.values():
            self._apply_decay(record)
        sorted_records = sorted(self._records.values(), key=lambda r: r.score, reverse=True)
        return sorted_records[:top_n]
