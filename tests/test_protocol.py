"""Tests for the TaoForge wire protocol (message types)."""

from taoforge.protocol import (
    BenchmarkChallengeMessage,
    ImprovementProposalMessage,
    ProofVerificationMessage,
)


def test_improvement_proposal_defaults():
    msg = ImprovementProposalMessage()
    assert msg.challenge_id == ""
    assert msg.proposal_id is None
    assert msg.improvement_claim is None


def test_improvement_proposal_serialize():
    msg = ImprovementProposalMessage(
        proposal_id="test-123",
        agent_hotkey="0xabc",
        mutation_type="lora_merge",
        improvement_claim=0.05,
        bond_amount=2.5,
    )
    data = msg.model_dump()
    assert data["proposal_id"] == "test-123"
    assert data["mutation_type"] == "lora_merge"
    assert data["improvement_claim"] == 0.05
    assert data["bond_amount"] == 2.5


def test_improvement_proposal_roundtrip():
    msg = ImprovementProposalMessage(
        proposal_id="test-456",
        mutation_type="tool_graph_rewire",
        improvement_claim=0.1,
    )
    json_str = msg.model_dump_json()
    restored = ImprovementProposalMessage.model_validate_json(json_str)
    assert restored.proposal_id == "test-456"
    assert restored.improvement_claim == 0.1


def test_benchmark_challenge():
    msg = BenchmarkChallengeMessage(
        challenge_id="ch-1",
        task_ids=["task_a", "task_b"],
        benchmark_version="v0.1",
    )
    assert len(msg.task_ids) == 2
    data = msg.model_dump()
    assert data["challenge_id"] == "ch-1"


def test_proof_verification():
    msg = ProofVerificationMessage(
        proof_bytes=b"\x00" * 64,
        circuit_type="improvement",
        public_inputs_json='{"benchmark_id": "bench_v0.1"}',
    )
    assert msg.circuit_type == "improvement"
    assert len(msg.proof_bytes) == 64
