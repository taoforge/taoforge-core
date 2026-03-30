"""Tests for the proposal system."""

import pytest

from taoforge.proposal.bond import BondManager
from taoforge.proposal.queue import ProposalQueue
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
    ProposalStatus,
)


def _make_proposal(**kwargs) -> ImprovementProposal:
    """Helper to create a valid proposal."""
    defaults = dict(
        agent_id="0xtest",
        mutation_type="lora_merge",
        baseline_proof=BaselineProof(zk_proof=b"\x00" * 64, benchmark_id="bench_v0.1", score_hash="abc"),
        delta_proof=DeltaProof(zk_proof=b"\x00" * 64, score_hash="def", improvement_claim=0.05),
        bond_amount=2.0,
    )
    defaults.update(kwargs)
    return ImprovementProposal(**defaults)


def test_proposal_validate_structure():
    p = _make_proposal()
    assert p.validate_structure() == []


def test_proposal_missing_agent():
    p = _make_proposal(agent_id="")
    errors = p.validate_structure()
    assert any("agent_id" in e for e in errors)


def test_proposal_improvement_claim():
    p = _make_proposal()
    assert p.improvement_claim == 0.05


def test_proposal_queue_submit():
    q = ProposalQueue(min_bond=1.0)
    p = _make_proposal(bond_amount=2.0)
    pid = q.submit(p)
    assert pid == p.proposal_id
    assert q.size == 1


def test_proposal_queue_min_bond():
    q = ProposalQueue(min_bond=5.0)
    p = _make_proposal(bond_amount=2.0)
    with pytest.raises(ValueError, match="below minimum"):
        q.submit(p)


def test_proposal_queue_pop():
    q = ProposalQueue(min_bond=1.0)
    p1 = _make_proposal(bond_amount=2.0)
    p2 = _make_proposal(bond_amount=5.0)
    q.submit(p1)
    q.submit(p2)
    # Should pop highest bond first
    popped = q.pop_next()
    assert popped.bond_amount == 5.0


def test_bond_manager_lock_and_return():
    bm = BondManager()
    bm.lock_bond("p1", "agent1", 3.0)
    assert bm.get_locked("agent1") == 3.0

    total = bm.return_bond("p1", bonus=0.5)
    assert total == 3.5
    assert bm.get_locked("agent1") == 0.0


def test_bond_manager_slash():
    bm = BondManager()
    bm.lock_bond("p1", "agent1", 3.0)
    slashed = bm.slash_bond("p1", "fraud")
    assert slashed == 3.0
    record = bm.get_record("p1")
    assert record.slashed is True
