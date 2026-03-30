"""Subnet adapter — translates between TaoForge's eval framework and subnet-specific evals."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from taoforge.evaluation.results import EvalResult, TaskScore
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import EvalTask
from taoforge.subnets.registry import SubnetProfile

logger = logging.getLogger(__name__)


class SubnetAdapter(ABC):
    """Abstract adapter between TaoForge and a specific subnet's evaluation.

    Each target subnet gets an adapter that knows how to:
    1. Translate the subnet's eval criteria into TaoForge benchmark tasks
    2. Run agents against the subnet's actual eval (competitor mode)
    3. Simulate the subnet's eval locally (offline mode)
    """

    def __init__(self, profile: SubnetProfile) -> None:
        self.profile = profile

    @abstractmethod
    def build_benchmark_suite(self) -> BenchmarkSuite:
        """Build a TaoForge BenchmarkSuite that mirrors this subnet's eval."""
        ...

    @abstractmethod
    def evaluate_on_subnet(self, agent: Any) -> EvalResult:
        """Run the agent against the actual subnet evaluation (competitor mode)."""
        ...

    @abstractmethod
    def evaluate_locally(self, agent: Any) -> EvalResult:
        """Simulate the subnet's evaluation locally (offline mode)."""
        ...

    def get_improvement_opportunity(self, current_result: EvalResult) -> dict:
        """Analyze where the agent can improve on this subnet.

        Returns a dict with:
        - weakest_areas: list of task IDs with lowest scores
        - suggested_mutations: mutation types likely to help
        - estimated_headroom: how much improvement is possible
        """
        if not current_result.task_scores:
            return {"weakest_areas": [], "suggested_mutations": [], "estimated_headroom": 1.0}

        sorted_scores = sorted(current_result.task_scores, key=lambda t: t.score)
        weakest = [t.task_id for t in sorted_scores[:3]]
        headroom = 1.0 - current_result.aggregate_score

        return {
            "weakest_areas": weakest,
            "suggested_mutations": self._suggest_mutations(weakest),
            "estimated_headroom": headroom,
        }

    def _suggest_mutations(self, weak_areas: list[str]) -> list[str]:
        """Suggest mutation types based on weak areas. Override per adapter."""
        return ["prompt_chain_refactor", "lora_merge"]


class TextPromptingAdapter(SubnetAdapter):
    """Adapter for text generation / prompting subnets (e.g. SN1)."""

    def build_benchmark_suite(self) -> BenchmarkSuite:
        from taoforge.evaluation.task import TextReasoningTask

        suite = BenchmarkSuite(
            suite_id=f"subnet_{self.profile.netuid}_text",
            version="0.1",
        )
        # Build tasks matching the subnet's eval criteria
        for criterion in self.profile.eval_criteria:
            suite.add_task(TextReasoningTask(
                task_id=f"sn{self.profile.netuid}_{criterion}",
                prompt=f"Evaluate {criterion} capability",
            ))
        return suite

    def evaluate_on_subnet(self, agent: Any) -> EvalResult:
        """Run agent against the actual prompting subnet."""
        # TODO: Register as miner on the subnet, submit responses, read scores
        logger.info(f"Evaluating on subnet {self.profile.netuid} (live mode) — not yet implemented")
        return EvalResult(suite_id=f"subnet_{self.profile.netuid}_live")

    def evaluate_locally(self, agent: Any) -> EvalResult:
        """Simulate the prompting subnet's evaluation locally."""
        suite = self.build_benchmark_suite()
        from taoforge.evaluation.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        return engine.run_suite(agent, suite)


class ImageGenerationAdapter(SubnetAdapter):
    """Adapter for image generation subnets (e.g. SN5)."""

    def build_benchmark_suite(self) -> BenchmarkSuite:
        suite = BenchmarkSuite(
            suite_id=f"subnet_{self.profile.netuid}_image",
            version="0.1",
        )
        for criterion in self.profile.eval_criteria:
            suite.add_task(EvalTaskStub(
                task_id=f"sn{self.profile.netuid}_{criterion}",
                category="image_gen",
            ))
        return suite

    def evaluate_on_subnet(self, agent: Any) -> EvalResult:
        logger.info(f"Evaluating on subnet {self.profile.netuid} (live mode) — not yet implemented")
        return EvalResult(suite_id=f"subnet_{self.profile.netuid}_live")

    def evaluate_locally(self, agent: Any) -> EvalResult:
        suite = self.build_benchmark_suite()
        from taoforge.evaluation.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        return engine.run_suite(agent, suite)


class EvalTaskStub(EvalTask):
    """Generic eval task stub for subnet adapters."""

    def __init__(self, task_id: str, category: str = "generic") -> None:
        self.task_id = task_id
        self.category = category
        self.description = f"Subnet eval: {task_id}"

    def run(self, agent: Any) -> TaskScore:
        return TaskScore(task_id=self.task_id, score=0.0)

    def validate_output(self, output: Any) -> bool:
        return output is not None


# Adapter factory
_ADAPTER_MAP: dict[str, type[SubnetAdapter]] = {
    "text_quality": TextPromptingAdapter,
    "image_quality": ImageGenerationAdapter,
}


def create_adapter(profile: SubnetProfile) -> SubnetAdapter:
    """Create the appropriate adapter for a subnet profile."""
    if profile.benchmark_type == "subnet_analysis":
        from taoforge.subnets.analysis_adapter import SubnetAnalysisAdapter
        return SubnetAnalysisAdapter(profile)
    adapter_cls = _ADAPTER_MAP.get(profile.benchmark_type, TextPromptingAdapter)
    return adapter_cls(profile)
