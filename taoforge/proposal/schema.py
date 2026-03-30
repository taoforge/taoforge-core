"""Core data structures for the improvement proposal system."""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


class ProposalStatus(enum.Enum):
    """Lifecycle states of an improvement proposal."""

    PENDING = "pending"
    VALIDATING = "validating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SLASHED = "slashed"


@dataclass
class BaselineProof:
    """ZK proof attesting to an agent's baseline evaluation score."""

    zk_proof: bytes
    benchmark_id: str
    score_hash: str


@dataclass
class DeltaProof:
    """ZK proof attesting to an agent's improved evaluation score."""

    zk_proof: bytes
    score_hash: str
    improvement_claim: float


@dataclass
class ImprovementProposal:
    """A complete improvement proposal submitted by a miner agent.

    Contains the mutation description, ZK proofs of baseline and improved
    performance, bonded stake, and DAG lineage information.
    """

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""  # Agent hotkey
    parent_delta: Optional[str] = None  # IPFS hash of parent improvement (DAG link)
    mutation_type: str = ""  # From MutationType enum
    baseline_proof: Optional[BaselineProof] = None
    delta_proof: Optional[DeltaProof] = None
    bond_amount: float = 0.0
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: ProposalStatus = ProposalStatus.PENDING

    @property
    def improvement_claim(self) -> float:
        """The claimed improvement percentage."""
        if self.delta_proof:
            return self.delta_proof.improvement_claim
        return 0.0

    def validate_structure(self) -> list[str]:
        """Check proposal for structural validity. Returns list of errors."""
        errors = []
        if not self.agent_id:
            errors.append("Missing agent_id (hotkey).")
        if not self.mutation_type:
            errors.append("Missing mutation_type.")
        if self.baseline_proof is None:
            errors.append("Missing baseline_proof.")
        if self.delta_proof is None:
            errors.append("Missing delta_proof.")
        if self.bond_amount <= 0:
            errors.append("Bond amount must be positive.")
        if self.delta_proof and self.delta_proof.improvement_claim <= 0:
            errors.append("Improvement claim must be positive.")
        return errors
