"""Bond management — lock, slash, and return bonded TAO for proposals."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class BondRecord:
    """Record of a locked bond."""

    proposal_id: str
    agent_id: str
    amount: float
    locked: bool = True
    slashed: bool = False
    returned: bool = False
    bonus: float = 0.0


class BondManager:
    """Manages TAO bonds for improvement proposals.

    Bonds are locked on submission, returned with bonus on acceptance,
    or slashed on fraud detection.
    """

    def __init__(self) -> None:
        self._bonds: dict[str, BondRecord] = {}
        self._agent_totals: dict[str, float] = {}
        self._lock = threading.Lock()

    def lock_bond(self, proposal_id: str, agent_id: str, amount: float) -> BondRecord:
        """Lock a bond for a proposal submission."""
        with self._lock:
            record = BondRecord(
                proposal_id=proposal_id,
                agent_id=agent_id,
                amount=amount,
            )
            self._bonds[proposal_id] = record
            self._agent_totals[agent_id] = self._agent_totals.get(agent_id, 0.0) + amount

            logger.info(
                f"Bond locked | proposal={proposal_id} | agent={agent_id[:16]}... | "
                f"amount={amount}"
            )
            return record

    def slash_bond(self, proposal_id: str, reason: str) -> Optional[float]:
        """Slash a bond for a fraudulent proposal. Returns slashed amount."""
        with self._lock:
            record = self._bonds.get(proposal_id)
            if record is None or not record.locked:
                return None

            record.slashed = True
            record.locked = False
            self._agent_totals[record.agent_id] -= record.amount

            logger.warning(
                f"Bond slashed | proposal={proposal_id} | "
                f"amount={record.amount} | reason={reason}"
            )
            return record.amount

    def return_bond(self, proposal_id: str, bonus: float = 0.0) -> Optional[float]:
        """Return a bond after successful proposal acceptance. Returns total amount."""
        with self._lock:
            record = self._bonds.get(proposal_id)
            if record is None or not record.locked:
                return None

            record.returned = True
            record.locked = False
            record.bonus = bonus
            total = record.amount + bonus
            self._agent_totals[record.agent_id] -= record.amount

            logger.info(
                f"Bond returned | proposal={proposal_id} | "
                f"amount={record.amount} + bonus={bonus} = {total}"
            )
            return total

    def get_locked(self, agent_id: str) -> float:
        """Get total locked bond amount for an agent."""
        return self._agent_totals.get(agent_id, 0.0)

    def get_record(self, proposal_id: str) -> Optional[BondRecord]:
        """Get the bond record for a proposal."""
        return self._bonds.get(proposal_id)
