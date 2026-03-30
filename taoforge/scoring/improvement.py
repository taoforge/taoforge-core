"""Delta_verified calculation — magnitude of verified improvement."""

from __future__ import annotations

from taoforge.evaluation.results import EvalResult, ScoreVector


def compute_delta_verified(baseline: EvalResult, delta: EvalResult) -> float:
    """Calculate the verified improvement magnitude.

    This is the core metric: how much better did the agent actually get
    across the benchmark suite, as independently verified by validators.

    Args:
        baseline: The agent's pre-mutation evaluation result.
        delta: The agent's post-mutation evaluation result.

    Returns:
        Normalized improvement score in [0, 1]. Returns 0 if no improvement.
    """
    if baseline.aggregate_score <= 0:
        return 0.0

    raw_improvement = delta.aggregate_score - baseline.aggregate_score
    if raw_improvement <= 0:
        return 0.0

    # Normalize: improvement as fraction of remaining headroom
    headroom = 1.0 - baseline.aggregate_score
    if headroom <= 0:
        return 0.0

    normalized = raw_improvement / headroom
    return min(max(normalized, 0.0), 1.0)
