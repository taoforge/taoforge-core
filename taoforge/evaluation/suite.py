"""Benchmark suite — collection of evaluation tasks."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from taoforge.evaluation.task import EvalTask


@dataclass
class BenchmarkSuite:
    """A versioned collection of evaluation tasks.

    Suites are immutable once published. New versions are created
    when tasks are added, removed, or rotated.
    """

    suite_id: str = ""
    version: str = "0.1"
    tasks: list[EvalTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    categories: set[str] = field(default_factory=set)

    def add_task(self, task: EvalTask) -> None:
        """Add a task to the suite."""
        self.tasks.append(task)
        self.categories.add(task.category)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID. Returns True if found and removed."""
        for i, task in enumerate(self.tasks):
            if task.task_id == task_id:
                self.tasks.pop(i)
                return True
        return False

    def get_task(self, task_id: str) -> EvalTask | None:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def sample(self, n: int, seed: int | None = None) -> list[EvalTask]:
        """Sample n random tasks from the suite (for holdout generation)."""
        rng = random.Random(seed)
        return rng.sample(self.tasks, min(n, len(self.tasks)))

    def get_by_category(self, category: str) -> list[EvalTask]:
        """Get all tasks in a given category."""
        return [t for t in self.tasks if t.category == category]

    @property
    def size(self) -> int:
        return len(self.tasks)

    @property
    def task_ids(self) -> list[str]:
        return [t.task_id for t in self.tasks]
