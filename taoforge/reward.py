"""Reward function — maps miner responses to scores."""

from __future__ import annotations

from taoforge.protocol import ImprovementProposalMessage


def reward(
    query: ImprovementProposalMessage,
    responses: list[dict | None],
) -> list[float]:
    """Compute rewards for a batch of miner responses.

    Wraps the composite scoring formula from taoforge.scoring and normalizes
    scores.

    Args:
        query: The original challenge message sent to miners.
        responses: List of miner response dicts (None for non-responders).

    Returns:
        List of reward floats, one per response.
    """
    scores = []
    for response in responses:
        if response is None or response.get("proposal_id") is None:
            scores.append(0.0)
            continue

        # TODO: Use taoforge.scoring.formula.compute_score()
        score = 0.0
        claim = response.get("improvement_claim")
        if claim is not None and claim > 0:
            score = min(float(claim), 1.0)
        scores.append(score)

    # Normalize to [0, 1] range
    max_score = max(scores) if scores else 0.0
    if max_score > 0:
        scores = [s / max_score for s in scores]

    return scores
