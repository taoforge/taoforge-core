"""Regression penalty — penalizes proposals that regress on some capabilities."""

from __future__ import annotations

from taoforge.evaluation.results import ScoreVector


def compute_regression_penalty(
    score_vector: ScoreVector,
    threshold: float = -0.01,
) -> float:
    """Compute penalty for capability regression.

    An improvement on target metrics shouldn't come at the cost of
    regression on other capabilities. This penalty discourages
    narrow optimization.

    Args:
        score_vector: The score comparison between baseline and delta.
        threshold: Per-task regression threshold (default: -1%).

    Returns:
        Regression penalty in [0, 1]. Higher = worse regression.
    """
    if not score_vector.per_task_deltas:
        return 0.0

    total_tasks = len(score_vector.per_task_deltas)
    if total_tasks == 0:
        return 0.0

    # Count regression severity
    regression_sum = 0.0
    for delta in score_vector.per_task_deltas.values():
        if delta < threshold:
            regression_sum += abs(delta)

    # Normalize by number of tasks and max possible regression
    regression_fraction = len(score_vector.regression_flags) / total_tasks
    regression_magnitude = min(regression_sum / total_tasks, 1.0)

    # Combined penalty: fraction of tasks regressed * magnitude
    penalty = regression_fraction * 0.5 + regression_magnitude * 0.5
    return min(max(penalty, 0.0), 1.0)
