"""Composite scoring formula — the core economic mechanism of TaoForge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from taoforge.evaluation.results import EvalResult, ScoreVector
from taoforge.proposal.schema import ImprovementProposal
from taoforge.scoring.breadth import compute_breadth
from taoforge.scoring.gaming import compute_gaming_penalty
from taoforge.scoring.improvement import compute_delta_verified
from taoforge.scoring.novelty import compute_novelty
from taoforge.scoring.regression import compute_regression_penalty
from taoforge.scoring.weights import ScoringWeights

if TYPE_CHECKING:
    from taoforge.registry.dag import ImprovementDAG


def compute_score(
    proposal: ImprovementProposal,
    baseline_result: EvalResult,
    delta_result: EvalResult,
    weights: ScoringWeights | None = None,
    dag: object | None = None,
    holdout_result: EvalResult | None = None,
    proposal_history: list[ImprovementProposal] | None = None,
) -> float:
    """Compute the composite score for an improvement proposal.

    score = w_improvement * Δ_verified
          + w_novelty    * novelty(mutation)
          + w_breadth    * breadth(Δ_scores)
          - w_regression * regression_penalty
          - w_gaming     * gaming_detection

    Args:
        proposal: The improvement proposal being scored.
        baseline_result: Agent's pre-mutation evaluation.
        delta_result: Agent's post-mutation evaluation.
        weights: Scoring hyperparameters (defaults to standard weights).
        dag: Improvement DAG for novelty assessment.
        holdout_result: Holdout set evaluation for gaming detection.
        proposal_history: Recent proposals for pattern detection.

    Returns:
        Composite score in [0, 1].
    """
    if weights is None:
        weights = ScoringWeights()

    # Compute score vector
    score_vector = ScoreVector.from_results(baseline_result, delta_result)

    # Individual components
    delta_verified = compute_delta_verified(baseline_result, delta_result)
    novelty = compute_novelty(proposal, dag)
    breadth = compute_breadth(score_vector)
    regression = compute_regression_penalty(score_vector)
    gaming = compute_gaming_penalty(
        proposal, delta_result, holdout_result, proposal_history
    )

    # Composite formula
    score = (
        weights.w_improvement * delta_verified
        + weights.w_novelty * novelty
        + weights.w_breadth * breadth
        - weights.w_regression * regression
        - weights.w_gaming * gaming
    )

    # Clamp to [0, 1]
    return min(max(score, 0.0), 1.0)
