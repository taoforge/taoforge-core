"""Benchmark engine — runs evaluation suites against agents."""

from __future__ import annotations

import logging
import time
from typing import Any

from taoforge.evaluation.results import EvalResult, ScoreVector, TaskScore
from taoforge.evaluation.suite import BenchmarkSuite

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Core evaluation runner.

    Executes benchmark suites against agents and produces EvalResults.
    Used by both miners (self-evaluation) and validators (verification).
    """

    def run_suite(self, agent: Any, suite: BenchmarkSuite) -> EvalResult:
        """Run an entire benchmark suite against an agent."""
        task_scores = []
        for task in suite.tasks:
            try:
                score = task.run(agent)
                task_scores.append(score)
            except Exception as e:
                logger.warning(f"Task {task.task_id} failed: {e}")
                task_scores.append(TaskScore(task_id=task.task_id, score=0.0))

        result = EvalResult(
            suite_id=suite.suite_id,
            task_scores=task_scores,
            timestamp=time.time(),
        )
        result.compute_aggregate()

        logger.info(
            f"Suite {suite.suite_id} complete | "
            f"tasks={len(task_scores)} | aggregate={result.aggregate_score:.4f}"
        )
        return result

    def run_task(self, agent: Any, task: Any) -> TaskScore:
        """Run a single evaluation task."""
        return task.run(agent)

    def compare(self, baseline: EvalResult, delta: EvalResult) -> ScoreVector:
        """Compare baseline and delta results to produce a ScoreVector."""
        return ScoreVector.from_results(baseline, delta)
