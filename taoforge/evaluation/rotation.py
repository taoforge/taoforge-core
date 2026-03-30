"""Benchmark rotation scheduler — prevents overfitting to static benchmarks."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from taoforge.evaluation.suite import BenchmarkSuite


@dataclass
class RotationSchedule:
    """A rotation event."""

    suite_id: str
    activated_at: float
    expires_at: float


class BenchmarkRotation:
    """Manages benchmark suite rotation.

    Suites rotate on a schedule unknown to miners to prevent overfitting.
    New tasks are added from a validator-curated pool.
    """

    def __init__(self, rotation_interval_hours: float = 24.0) -> None:
        self.rotation_interval = rotation_interval_hours * 3600
        self._suites: dict[str, BenchmarkSuite] = {}
        self._current_suite_id: str = ""
        self._history: list[RotationSchedule] = []
        self._last_rotation: float = 0.0

    def register_suite(self, suite: BenchmarkSuite) -> None:
        """Register a benchmark suite for rotation."""
        self._suites[suite.suite_id] = suite
        if not self._current_suite_id:
            self._current_suite_id = suite.suite_id
            self._last_rotation = time.time()

    def get_current_suite(self) -> BenchmarkSuite | None:
        """Get the currently active benchmark suite."""
        return self._suites.get(self._current_suite_id)

    def should_rotate(self) -> bool:
        """Check if it's time to rotate to a new suite."""
        return time.time() - self._last_rotation > self.rotation_interval

    def rotate(self) -> BenchmarkSuite | None:
        """Rotate to the next benchmark suite.

        TODO: Implement rotation strategy (round-robin, weighted random,
        validator-curated selection).
        """
        available = [sid for sid in self._suites if sid != self._current_suite_id]
        if not available:
            return self.get_current_suite()

        # Simple round-robin for now
        next_id = available[0]
        now = time.time()

        self._history.append(
            RotationSchedule(
                suite_id=self._current_suite_id,
                activated_at=self._last_rotation,
                expires_at=now,
            )
        )

        self._current_suite_id = next_id
        self._last_rotation = now
        return self._suites[next_id]

    @property
    def current_suite_id(self) -> str:
        return self._current_suite_id
