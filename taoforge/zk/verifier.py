"""High-level ZK proof verification API for validators."""

from __future__ import annotations

import logging

from taoforge.zk.bridge import verify_proof
from taoforge.zk.types import ZKProof

logger = logging.getLogger(__name__)


class Verifier:
    """High-level proof verification API.

    Validators use this to verify ZK proofs submitted by miners.
    """

    def verify(self, proof: ZKProof) -> bool:
        """Verify a single ZK proof."""
        result = verify_proof(
            circuit_type=proof.circuit_type,
            proof_bytes=proof.proof_bytes,
            public_inputs=proof.public_inputs,
        )

        logger.debug(f"Proof verified | type={proof.circuit_type} | valid={result}")
        return result

    def batch_verify(self, proofs: list[ZKProof]) -> list[bool]:
        """Verify multiple ZK proofs."""
        # TODO: Implement batch verification for efficiency
        return [self.verify(proof) for proof in proofs]
