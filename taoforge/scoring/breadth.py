"""Breadth scoring — rewards improvement across diverse task categories."""

from __future__ import annotations

from taoforge.evaluation.results import ScoreVector


def compute_breadth(score_vector: ScoreVector) -> float:
    """Score how broadly the improvement spans across task categories.

    Rewards improvements that span diverse task categories rather than
    optimizing a single narrow benchmark.

    Args:
        score_vector: The score comparison between baseline and delta.

    Returns:
        Breadth score in [0, 1]. Higher = more broadly improved.
    """
    if not score_vector.per_task_deltas:
        return 0.0

    # Fraction of tasks that improved
    return score_vector.breadth
