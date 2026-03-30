"""Anti-gaming detection score — penalizes benchmark-specific gaming."""

from __future__ import annotations

from taoforge.evaluation.results import EvalResult
from taoforge.proposal.schema import ImprovementProposal


def compute_gaming_penalty(
    proposal: ImprovementProposal,
    public_result: EvalResult,
    holdout_result: EvalResult | None = None,
    history: list[ImprovementProposal] | None = None,
) -> float:
    """Detect benchmark-specific gaming.

    Compares public benchmark performance against holdout set performance.
    Large discrepancies suggest the agent is gaming specific benchmarks
    rather than genuinely improving.

    Args:
        proposal: The improvement proposal being scored.
        public_result: Evaluation result on public benchmarks.
        holdout_result: Evaluation result on validator holdout set.
        history: Recent proposals from this agent for pattern detection.

    Returns:
        Gaming penalty in [0, 1]. Higher = more likely gaming.
    """
    penalty = 0.0

    # Public vs holdout discrepancy
    if holdout_result is not None and public_result.aggregate_score > 0:
        discrepancy = public_result.aggregate_score - holdout_result.aggregate_score
        if discrepancy > 0.1:  # Public score > holdout by more than 10%
            penalty += min(discrepancy, 0.5)

    # Repeated small claims from same agent (potential grinding)
    if history:
        recent = [p for p in history if p.agent_id == proposal.agent_id]
        if len(recent) > 5:
            avg_claim = sum(p.improvement_claim for p in recent) / len(recent)
            if avg_claim < 0.005:  # Very small claims suggest gaming
                penalty += 0.2

    return min(max(penalty, 0.0), 1.0)
