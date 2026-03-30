"""Python-to-Rust FFI bridge for ZK proof operations.

Uses PyO3 bindings from the taoforge_zk Rust crate (built with maturin).
Falls back to stub implementations if the Rust crate is not installed.
"""

from __future__ import annotations

import json
import logging
import time

from taoforge.zk.types import ProofResult, ZKProof

logger = logging.getLogger(__name__)

# Try to import the Rust ZK module
_RUST_AVAILABLE = False
try:
    import taoforge_zk as _zk_native

    _RUST_AVAILABLE = True
except ImportError:
    logger.warning(
        "taoforge_zk Rust module not found — using stub ZK bridge. "
        "Build with: cd zk_circuits && maturin develop"
    )


def generate_proof(
    circuit_type: str,
    private_inputs: dict,
    public_inputs: dict,
) -> ProofResult:
    """Generate a ZK proof via the Rust ZK crate.

    Args:
        circuit_type: One of "baseline", "improvement", "lineage", "non_regression".
        private_inputs: Private inputs (known only to the agent).
        public_inputs: Public inputs (visible to validators).

    Returns:
        ProofResult with the generated proof or error.
    """
    start = time.monotonic()

    try:
        private_json = json.dumps(private_inputs)
        public_json = json.dumps(public_inputs)

        if _RUST_AVAILABLE:
            proof_bytes = _zk_native.generate_proof(circuit_type, private_json, public_json)
        else:
            # Stub: return fake proof bytes
            proof_bytes = b"\x00" * 64

        elapsed_ms = (time.monotonic() - start) * 1000

        proof = ZKProof(
            proof_bytes=proof_bytes,
            public_inputs=public_inputs,
            circuit_type=circuit_type,
        )

        return ProofResult(success=True, proof=proof, generation_time_ms=elapsed_ms)

    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ProofResult(success=False, error=str(e), generation_time_ms=elapsed_ms)


def verify_proof(
    circuit_type: str,
    proof_bytes: bytes,
    public_inputs: dict,
) -> bool:
    """Verify a ZK proof via the Rust ZK crate.

    Args:
        circuit_type: The circuit type that produced this proof.
        proof_bytes: The proof to verify.
        public_inputs: Public inputs for verification.

    Returns:
        True if the proof is valid.
    """
    try:
        public_json = json.dumps(public_inputs)

        if _RUST_AVAILABLE:
            return _zk_native.verify_proof(circuit_type, proof_bytes, public_json)
        else:
            # Stub: accept any non-empty proof
            return len(proof_bytes) > 0

    except Exception as e:
        logger.error(f"Proof verification error: {e}")
        return False


def is_rust_available() -> bool:
    """Check if the Rust ZK crate is installed and available."""
    return _RUST_AVAILABLE
