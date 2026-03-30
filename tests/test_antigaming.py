"""Tests for anti-gaming mechanisms."""

from taoforge.antigaming.bond_slashing import SlashingEvaluator
from taoforge.antigaming.cross_validation import CrossValidator
from taoforge.antigaming.detector import GamingDetector
from taoforge.evaluation.results import EvalResult, TaskScore
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
)


def _make_proposal(agent_id="a1", improvement=0.05):
    return ImprovementProposal(
        agent_id=agent_id,
        mutation_type="lora_merge",
        baseline_proof=BaselineProof(zk_proof=b"", benchmark_id="b1", score_hash="h"),
        delta_proof=DeltaProof(zk_proof=b"", score_hash="h2", improvement_claim=improvement),
        bond_amount=2.0,
    )


def test_gaming_detector_no_holdout():
    detector = GamingDetector()
    proposal = _make_proposal()
    public = EvalResult(suite_id="b1", aggregate_score=0.7)
    report = detector.detect(proposal, public)
    assert not report.is_suspicious


def test_gaming_detector_holdout_discrepancy():
    detector = GamingDetector(suspicion_threshold=0.05)
    proposal = _make_proposal()
    public = EvalResult(suite_id="b1", aggregate_score=0.9)
    holdout = EvalResult(suite_id="holdout", aggregate_score=0.5)
    report = detector.detect(proposal, public, holdout_result=holdout)
    assert report.is_suspicious
    assert "holdout" in report.reasons[0].lower()


def test_slashing_evaluator_proof_fails():
    evaluator = SlashingEvaluator()
    proposal = _make_proposal(improvement=0.1)
    validator_result = EvalResult(suite_id="b1", aggregate_score=0.6)
    baseline_result = EvalResult(suite_id="b1", aggregate_score=0.5)
    decision = evaluator.evaluate(proposal, 0.1, validator_result, baseline_result, proof_valid=False)
    assert decision.should_slash
    assert "proof" in decision.reason.lower()


def test_slashing_evaluator_not_reproducible():
    evaluator = SlashingEvaluator()
    proposal = _make_proposal(improvement=0.1)
    validator_result = EvalResult(suite_id="b1", aggregate_score=0.45)
    baseline_result = EvalResult(suite_id="b1", aggregate_score=0.5)
    decision = evaluator.evaluate(proposal, 0.1, validator_result, baseline_result, proof_valid=True)
    assert decision.should_slash


def test_cross_validator_trust():
    cv = CrossValidator()
    scores = {0: 0.5, 1: 0.52, 2: 0.48, 3: 0.9}  # Validator 3 is outlier
    trust = cv.record_scores("p1", scores)
    assert trust[3] < trust[0]


def test_cross_validator_outliers():
    cv = CrossValidator(deviation_threshold=0.1)
    for i in range(10):
        cv.record_scores(f"p{i}", {0: 0.5, 1: 0.5, 2: 0.5, 3: 0.95})
    outliers = cv.get_outliers(threshold=0.8)
    assert 3 in outliers
