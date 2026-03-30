"""Bonded proposal queue — priority queue sorted by bond amount."""

from __future__ import annotations

import heapq
import threading
from typing import Optional

import logging

from taoforge.proposal.schema import ImprovementProposal, ProposalStatus

logger = logging.getLogger(__name__)


class ProposalQueue:
    """Priority queue for improvement proposals, sorted by bond amount (descending).

    Higher bonds indicate higher confidence and get processed first.
    Enforces minimum bond threshold.
    """

    def __init__(self, min_bond: float = 1.0) -> None:
        self.min_bond = min_bond
        self._heap: list[tuple[float, str, ImprovementProposal]] = []
        self._proposals: dict[str, ImprovementProposal] = {}
        self._lock = threading.Lock()

    def submit(self, proposal: ImprovementProposal) -> str:
        """Submit a proposal to the queue. Returns proposal_id.

        Raises ValueError if bond is below minimum or proposal is structurally invalid.
        """
        errors = proposal.validate_structure()
        if errors:
            raise ValueError(f"Invalid proposal: {'; '.join(errors)}")

        if proposal.bond_amount < self.min_bond:
            raise ValueError(
                f"Bond {proposal.bond_amount} below minimum {self.min_bond} TAO."
            )

        with self._lock:
            # Negative bond for max-heap behavior with heapq (min-heap)
            heapq.heappush(
                self._heap,
                (-proposal.bond_amount, proposal.proposal_id, proposal),
            )
            self._proposals[proposal.proposal_id] = proposal

        logger.info(
            f"Proposal queued | id={proposal.proposal_id} | "
            f"bond={proposal.bond_amount} | type={proposal.mutation_type}"
        )
        return proposal.proposal_id

    def pop_next(self) -> Optional[ImprovementProposal]:
        """Pop the highest-bonded pending proposal."""
        with self._lock:
            while self._heap:
                _, pid, proposal = heapq.heappop(self._heap)
                if proposal.status == ProposalStatus.PENDING:
                    proposal.status = ProposalStatus.VALIDATING
                    return proposal
        return None

    def get_pending(self) -> list[ImprovementProposal]:
        """Get all pending proposals (read-only snapshot)."""
        with self._lock:
            return [
                p for p in self._proposals.values()
                if p.status == ProposalStatus.PENDING
            ]

    def accept(self, proposal_id: str) -> None:
        """Mark a proposal as accepted."""
        with self._lock:
            if proposal_id in self._proposals:
                self._proposals[proposal_id].status = ProposalStatus.ACCEPTED

    def reject(self, proposal_id: str) -> None:
        """Mark a proposal as rejected."""
        with self._lock:
            if proposal_id in self._proposals:
                self._proposals[proposal_id].status = ProposalStatus.REJECTED

    def slash(self, proposal_id: str) -> None:
        """Mark a proposal as slashed (fraudulent)."""
        with self._lock:
            if proposal_id in self._proposals:
                self._proposals[proposal_id].status = ProposalStatus.SLASHED

    @property
    def size(self) -> int:
        return len([p for p in self._proposals.values() if p.status == ProposalStatus.PENDING])
