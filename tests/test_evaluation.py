"""Tests for the evaluation engine and task system."""

from taoforge.evaluation.results import EvalResult, ScoreVector, TaskScore
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import TextReasoningTask, CodeGenerationTask


def test_task_score():
    ts = TaskScore(task_id="t1", score=0.85)
    assert ts.score == 0.85


def test_eval_result_aggregate():
    result = EvalResult(
        suite_id="s1",
        task_scores=[
            TaskScore(task_id="t1", score=0.8),
            TaskScore(task_id="t2", score=0.6),
        ],
    )
    agg = result.compute_aggregate()
    assert abs(agg - 0.7) < 0.001


def test_score_vector_from_results():
    baseline = EvalResult(
        suite_id="s1",
        task_scores=[
            TaskScore(task_id="t1", score=0.5),
            TaskScore(task_id="t2", score=0.6),
        ],
        aggregate_score=0.55,
    )
    delta = EvalResult(
        suite_id="s1",
        task_scores=[
            TaskScore(task_id="t1", score=0.7),
            TaskScore(task_id="t2", score=0.55),  # Regression
        ],
        aggregate_score=0.625,
    )
    sv = ScoreVector.from_results(baseline, delta)
    assert sv.improvement_delta > 0
    assert "t2" in sv.regression_flags
    assert sv.has_regressions


def test_score_vector_breadth():
    sv = ScoreVector(
        per_task_deltas={"t1": 0.1, "t2": 0.05, "t3": -0.02},
    )
    # 2 out of 3 improved
    assert abs(sv.breadth - 2 / 3) < 0.001


def test_benchmark_suite():
    suite = BenchmarkSuite(suite_id="bench_v0.1")
    suite.add_task(TextReasoningTask("r1", "What is 2+2?"))
    suite.add_task(CodeGenerationTask("c1", "Write fizzbuzz"))
    assert suite.size == 2
    assert "reasoning" in suite.categories
    assert "code" in suite.categories


def test_benchmark_suite_sample():
    suite = BenchmarkSuite(suite_id="bench_v0.1")
    for i in range(10):
        suite.add_task(TextReasoningTask(f"r{i}", f"Question {i}"))
    sample = suite.sample(3, seed=42)
    assert len(sample) == 3
