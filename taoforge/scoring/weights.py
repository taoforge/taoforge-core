"""Scoring weight configuration — the 5-weight hyperparameters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """Hyperparameter weights for the composite scoring formula.

    score = w_improvement * Δ_verified
          + w_novelty    * novelty(mutation)
          + w_breadth    * breadth(Δ_scores)
          - w_regression * regression_penalty
          - w_gaming     * gaming_detection

    Defaults match the TaoForge architecture specification.
    """

    w_improvement: float = 0.35
    w_novelty: float = 0.25
    w_breadth: float = 0.20
    w_regression: float = 0.15
    w_gaming: float = 0.05

    @property
    def total(self) -> float:
        """Sum of all weights (should be ~1.0)."""
        return (
            self.w_improvement
            + self.w_novelty
            + self.w_breadth
            + self.w_regression
            + self.w_gaming
        )

    def validate(self) -> list[str]:
        """Validate weight configuration."""
        errors = []
        for name in ["w_improvement", "w_novelty", "w_breadth", "w_regression", "w_gaming"]:
            val = getattr(self, name)
            if val < 0 or val > 1:
                errors.append(f"{name}={val} must be in [0, 1].")
        if abs(self.total - 1.0) > 0.01:
            errors.append(f"Weights sum to {self.total}, expected ~1.0.")
        return errors
