"""Holdout set management — validator-private evaluation tasks."""

from __future__ import annotations

import random

from taoforge.evaluation.results import EvalResult, TaskScore
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import EvalTask


class HoldoutManager:
    """Manages private holdout evaluation sets for validators.

    Holdout tasks are never seen by miners and are used for:
    - Novelty assessment
    - Regression detection
    - Anti-gaming verification
    """

    def __init__(self, holdout_fraction: float = 0.2, seed: int = 42) -> None:
        self.holdout_fraction = holdout_fraction
        self.seed = seed
        self._holdout_tasks: list[EvalTask] = []

    def generate_holdout(self, suite: BenchmarkSuite) -> list[EvalTask]:
        """Generate a holdout set from a benchmark suite.

        Samples a fraction of tasks to keep private. These tasks
        are removed from the public suite version that miners see.

        Args:
            suite: The full benchmark suite.

        Returns:
            List of holdout tasks.
        """
        n = max(1, int(len(suite.tasks) * self.holdout_fraction))
        self._holdout_tasks = suite.sample(n, seed=self.seed)
        return self._holdout_tasks

    def evaluate_holdout(self, agent: object) -> EvalResult:
        """Run the holdout set against an agent.

        Args:
            agent: The agent to evaluate.

        Returns:
            EvalResult for the holdout tasks only.
        """
        task_scores = []
        for task in self._holdout_tasks:
            try:
                score = task.run(agent)
                task_scores.append(score)
            except Exception:
                task_scores.append(TaskScore(task_id=task.task_id, score=0.0))

        result = EvalResult(
            suite_id="holdout",
            task_scores=task_scores,
        )
        result.compute_aggregate()
        return result

    @property
    def holdout_task_ids(self) -> list[str]:
        return [t.task_id for t in self._holdout_tasks]

    @property
    def size(self) -> int:
        return len(self._holdout_tasks)
