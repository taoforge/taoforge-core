"""Tests for the scoring formula and reward function."""

from taoforge.evaluation.results import EvalResult, ScoreVector, TaskScore
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
)
from taoforge.scoring.breadth import compute_breadth
from taoforge.scoring.formula import compute_score
from taoforge.scoring.improvement import compute_delta_verified
from taoforge.scoring.regression import compute_regression_penalty
from taoforge.scoring.weights import ScoringWeights


def test_scoring_weights_defaults():
    w = ScoringWeights()
    assert abs(w.total - 1.0) < 0.001


def test_scoring_weights_validate():
    w = ScoringWeights()
    assert w.validate() == []


def test_delta_verified_improvement():
    baseline = EvalResult(suite_id="s1", aggregate_score=0.5)
    delta = EvalResult(suite_id="s1", aggregate_score=0.7)
    dv = compute_delta_verified(baseline, delta)
    assert dv > 0
    # Improvement is 0.2 out of 0.5 headroom = 0.4
    assert abs(dv - 0.4) < 0.001


def test_delta_verified_no_improvement():
    baseline = EvalResult(suite_id="s1", aggregate_score=0.5)
    delta = EvalResult(suite_id="s1", aggregate_score=0.4)
    assert compute_delta_verified(baseline, delta) == 0.0


def test_breadth_all_improved():
    sv = ScoreVector(per_task_deltas={"t1": 0.1, "t2": 0.05})
    assert compute_breadth(sv) == 1.0


def test_regression_penalty():
    sv = ScoreVector(
        per_task_deltas={"t1": 0.1, "t2": -0.1, "t3": -0.05},
        regression_flags=["t2", "t3"],
    )
    penalty = compute_regression_penalty(sv)
    assert penalty > 0


def test_compute_score_positive():
    proposal = ImprovementProposal(
        agent_id="test",
        mutation_type="lora_merge",
        baseline_proof=BaselineProof(zk_proof=b"", benchmark_id="b1", score_hash="h1"),
        delta_proof=DeltaProof(zk_proof=b"", score_hash="h2", improvement_claim=0.1),
        bond_amount=2.0,
    )
    baseline = EvalResult(
        suite_id="b1",
        task_scores=[TaskScore("t1", 0.5), TaskScore("t2", 0.5)],
        aggregate_score=0.5,
    )
    delta = EvalResult(
        suite_id="b1",
        task_scores=[TaskScore("t1", 0.7), TaskScore("t2", 0.6)],
        aggregate_score=0.65,
    )
    score = compute_score(proposal, baseline, delta)
    assert 0 <= score <= 1
    assert score > 0
