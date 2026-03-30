"""Benchmark rotation enforcement — ensures proposals reference current benchmarks."""

from __future__ import annotations

from taoforge.evaluation.rotation import BenchmarkRotation
from taoforge.proposal.schema import ImprovementProposal


class RotationEnforcer:
    """Enforces that proposals reference the currently active benchmark suite.

    Rejects proposals that target expired or future benchmark versions.
    """

    def __init__(self, rotation: BenchmarkRotation) -> None:
        self.rotation = rotation

    def validate_benchmark_id(self, proposal: ImprovementProposal) -> bool:
        """Check that the proposal's benchmark_id matches the current suite.

        Returns True if valid.
        """
        current = self.rotation.get_current_suite()
        if current is None:
            return False

        if proposal.baseline_proof is None:
            return False

        return proposal.baseline_proof.benchmark_id == current.suite_id

    def get_current_benchmark_id(self) -> str:
        """Get the currently valid benchmark ID."""
        current = self.rotation.get_current_suite()
        return current.suite_id if current else ""
