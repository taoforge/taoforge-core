"""Evaluation result data structures."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskScore:
    """Score for a single evaluation task."""

    task_id: str
    score: float  # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of running a full benchmark suite."""

    suite_id: str
    task_scores: list[TaskScore] = field(default_factory=list)
    aggregate_score: float = 0.0
    timestamp: float = 0.0

    def compute_aggregate(self) -> float:
        """Compute aggregate score as mean of task scores."""
        if not self.task_scores:
            return 0.0
        self.aggregate_score = sum(t.score for t in self.task_scores) / len(self.task_scores)
        return self.aggregate_score


@dataclass
class ScoreVector:
    """Comparison between baseline and delta evaluation results."""

    improvement_delta: float = 0.0  # Overall improvement
    per_task_deltas: dict[str, float] = field(default_factory=dict)
    regression_flags: list[str] = field(default_factory=list)  # Task IDs with regressions

    @property
    def has_regressions(self) -> bool:
        return len(self.regression_flags) > 0

    @property
    def breadth(self) -> float:
        """Fraction of tasks that improved."""
        if not self.per_task_deltas:
            return 0.0
        improved = sum(1 for d in self.per_task_deltas.values() if d > 0)
        return improved / len(self.per_task_deltas)

    @classmethod
    def from_results(
        cls, baseline: EvalResult, delta: EvalResult, regression_threshold: float = -0.01
    ) -> ScoreVector:
        """Compute a ScoreVector from baseline and delta EvalResults."""
        per_task = {}
        regressions = []

        baseline_map = {t.task_id: t.score for t in baseline.task_scores}
        delta_map = {t.task_id: t.score for t in delta.task_scores}

        for task_id in baseline_map:
            if task_id in delta_map:
                diff = delta_map[task_id] - baseline_map[task_id]
                per_task[task_id] = diff
                if diff < regression_threshold:
                    regressions.append(task_id)

        return cls(
            improvement_delta=delta.aggregate_score - baseline.aggregate_score,
            per_task_deltas=per_task,
            regression_flags=regressions,
        )
