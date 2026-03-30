"""Domain-agnostic environment layer for open-ended agent evaluation."""

from taoforge.environments.base import (
    CycleState,
    Environment,
    EnvironmentContext,
    GroundingResult,
)
from taoforge.environments.harness import EnvironmentHarness

__all__ = [
    "Environment",
    "EnvironmentContext",
    "GroundingResult",
    "CycleState",
    "EnvironmentHarness",
]
