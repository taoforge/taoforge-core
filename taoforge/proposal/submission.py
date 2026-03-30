"""Proposal submission pipeline — miner-side orchestration."""

from __future__ import annotations

from typing import Optional

import logging

from taoforge.proposal.bond import BondManager

logger = logging.getLogger(__name__)
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
)


class SubmissionPipeline:
    """Orchestrates the proposal submission flow from the miner side.

    Steps:
    1. Validate proposal structure.
    2. Check minimum bond requirements.
    3. Pin mutation delta to IPFS.
    4. Generate stealth address (if configured).
    5. Lock bond.
    6. Return prepared proposal ready for synapse population.
    """

    def __init__(self, bond_manager: BondManager, min_bond: float = 1.0) -> None:
        self.bond_manager = bond_manager
        self.min_bond = min_bond

    def prepare_proposal(
        self,
        agent_id: str,
        mutation_type: str,
        baseline_proof: BaselineProof,
        delta_proof: DeltaProof,
        bond_amount: float,
        parent_delta: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ImprovementProposal:
        """Prepare and validate a proposal for submission.

        Args:
            agent_id: The miner's hotkey.
            mutation_type: Type of mutation applied.
            baseline_proof: ZK proof of baseline score.
            delta_proof: ZK proof of improved score.
            bond_amount: TAO to bond.
            parent_delta: IPFS hash of parent improvement (for DAG lineage).
            metadata: Additional metadata (mutation description, novelty claim, etc.).

        Returns:
            A validated ImprovementProposal ready for submission.

        Raises:
            ValueError: If proposal is invalid or bond is insufficient.
        """
        if bond_amount < self.min_bond:
            raise ValueError(
                f"Bond {bond_amount} TAO below minimum {self.min_bond} TAO."
            )

        proposal = ImprovementProposal(
            agent_id=agent_id,
            mutation_type=mutation_type,
            baseline_proof=baseline_proof,
            delta_proof=delta_proof,
            bond_amount=bond_amount,
            parent_delta=parent_delta,
            metadata=metadata or {},
        )

        # Validate structure
        errors = proposal.validate_structure()
        if errors:
            raise ValueError(f"Invalid proposal: {'; '.join(errors)}")

        # Lock bond
        self.bond_manager.lock_bond(
            proposal_id=proposal.proposal_id,
            agent_id=agent_id,
            amount=bond_amount,
        )

        # TODO: Pin mutation delta to IPFS
        # delta_cid = ipfs.pin_mutation_delta(mutation_delta_bytes)

        # TODO: Generate stealth address if privacy mode enabled
        # stealth_addr = stealth.generate_stealth_address(agent_id)

        logger.info(
            f"Proposal prepared | id={proposal.proposal_id} | "
            f"type={mutation_type} | claim={delta_proof.improvement_claim:.4f}"
        )

        return proposal
