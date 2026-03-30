"""Novelty scoring — how novel is the proposed mutation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from taoforge.proposal.schema import ImprovementProposal

if TYPE_CHECKING:
    from taoforge.registry.dag import ImprovementDAG


def compute_novelty(proposal: ImprovementProposal, dag: ImprovementDAG | None = None) -> float:
    """Score how novel a mutation is.

    Novelty is assessed based on:
    - Is this mutation type new to the registry?
    - Is it the first to improve on this benchmark version?
    - Is it a compound mutation not seen before?
    - How different is it from recent proposals?

    Args:
        proposal: The improvement proposal to assess.
        dag: The improvement DAG for historical context (optional).

    Returns:
        Novelty score in [0, 1]. Higher = more novel.
    """
    score = 0.0

    # Base novelty for mutation type
    # Compound mutations get higher base novelty
    if proposal.mutation_type == "compound":
        score += 0.4
    else:
        score += 0.2

    # TODO: Check against DAG history:
    # - How many proposals of this mutation_type exist?
    # - When was the last proposal of this type?
    # - Is this benchmark_id new?

    if dag is not None:
        # Placeholder: novelty decreases with more similar proposals
        pass

    # Novelty claim bonus
    if proposal.metadata.get("novelty_claim"):
        score += 0.1

    return min(max(score, 0.0), 1.0)
