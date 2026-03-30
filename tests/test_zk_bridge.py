"""Tests for the ZK bridge (Python side — works with or without Rust crate)."""

from taoforge.zk.bridge import generate_proof, verify_proof
from taoforge.zk.types import ProofRequest, ProofResult, ZKProof


def test_generate_proof_stub():
    result = generate_proof(
        circuit_type="improvement",
        private_inputs={"base_score": 0.5, "delta_score": 0.7},
        public_inputs={"benchmark_id": "bench_v0.1", "improvement_claim": 0.2},
    )
    assert isinstance(result, ProofResult)
    assert result.success
    assert result.proof is not None
    assert len(result.proof.proof_bytes) > 0
    assert result.generation_time_ms >= 0


def test_verify_proof_stub():
    result = generate_proof(
        circuit_type="baseline",
        private_inputs={"score": 0.5},
        public_inputs={"benchmark_id": "bench_v0.1"},
    )
    assert result.proof is not None

    is_valid = verify_proof(
        circuit_type="baseline",
        proof_bytes=result.proof.proof_bytes,
        public_inputs={"benchmark_id": "bench_v0.1"},
    )
    assert is_valid


def test_empty_proof_invalid():
    is_valid = verify_proof(
        circuit_type="improvement",
        proof_bytes=b"",
        public_inputs={},
    )
    assert not is_valid


def test_zk_proof_dataclass():
    proof = ZKProof(
        proof_bytes=b"\x00" * 64,
        public_inputs={"benchmark_id": "b1"},
        circuit_type="improvement",
    )
    assert proof.circuit_type == "improvement"
    assert len(proof.proof_bytes) == 64


def test_all_circuit_types():
    for circuit_type in ["baseline", "improvement", "lineage", "non_regression"]:
        result = generate_proof(
            circuit_type=circuit_type,
            private_inputs={},
            public_inputs={},
        )
        assert result.success, f"Failed for circuit type: {circuit_type}"
