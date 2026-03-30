"""Evaluation task definitions — ABC and concrete task implementations."""

from __future__ import annotations

import abc
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from taoforge.agent.base import Agent, GenerationResult
from taoforge.evaluation.results import TaskScore

logger = logging.getLogger(__name__)


class EvalTask(abc.ABC):
    """Abstract base class for evaluation tasks.

    Each task defines a specific capability test that agents are evaluated against.
    """

    task_id: str = ""
    category: str = ""
    description: str = ""

    @abc.abstractmethod
    def run(self, agent: Agent) -> TaskScore:
        """Run this evaluation task against an agent."""
        ...

    @abc.abstractmethod
    def validate_output(self, output: Any) -> bool:
        """Validate that an agent's output is well-formed."""
        ...


class TextReasoningTask(EvalTask):
    """Evaluate text reasoning capabilities.

    Sends a prompt to the agent and scores the response based on:
    - Whether it contains expected keywords/patterns
    - Response length (penalize too short/too long)
    - Coherence heuristics
    """

    category = "reasoning"

    def __init__(
        self,
        task_id: str,
        prompt: str,
        expected_pattern: str = "",
        expected_keywords: list[str] | None = None,
        min_length: int = 10,
        max_length: int = 5000,
    ) -> None:
        self.task_id = task_id
        self.prompt = prompt
        self.expected_pattern = expected_pattern
        self.expected_keywords = expected_keywords or []
        self.min_length = min_length
        self.max_length = max_length
        self.description = f"Text reasoning: {task_id}"

    def run(self, agent: Agent) -> TaskScore:
        result = agent.generate(self.prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        score = self._score_response(result.text)
        return TaskScore(
            task_id=self.task_id,
            score=score,
            metadata={
                "response_length": len(result.text),
                "latency_ms": result.latency_ms,
                "tokens_used": result.tokens_used,
            },
        )

    def _score_response(self, text: str) -> float:
        if not text:
            return 0.0

        scores = []

        # Length score
        if len(text) < self.min_length:
            scores.append(len(text) / self.min_length)
        elif len(text) > self.max_length:
            scores.append(max(0.5, 1.0 - (len(text) - self.max_length) / self.max_length))
        else:
            scores.append(1.0)

        # Pattern matching
        if self.expected_pattern:
            if re.search(self.expected_pattern, text, re.IGNORECASE):
                scores.append(1.0)
            else:
                scores.append(0.0)

        # Keyword coverage
        if self.expected_keywords:
            found = sum(1 for kw in self.expected_keywords if kw.lower() in text.lower())
            scores.append(found / len(self.expected_keywords))

        return sum(scores) / len(scores) if scores else 0.0

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, str) and len(output) > 0


class CodeGenerationTask(EvalTask):
    """Evaluate code generation capabilities.

    Sends a coding prompt, extracts code from the response,
    and optionally runs test cases against it.
    """

    category = "code"

    def __init__(
        self,
        task_id: str,
        prompt: str,
        test_cases: list[dict] | None = None,
        language: str = "python",
    ) -> None:
        self.task_id = task_id
        self.prompt = prompt
        self.test_cases = test_cases or []
        self.language = language
        self.description = f"Code generation: {task_id}"

    def run(self, agent: Agent) -> TaskScore:
        result = agent.generate(self.prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        code = self._extract_code(result.text)
        if not code:
            return TaskScore(
                task_id=self.task_id, score=0.1,
                metadata={"reason": "no code block found"},
            )

        # Score based on test cases if provided
        if self.test_cases:
            passed, total = self._run_tests(code)
            score = passed / total if total > 0 else 0.0
        else:
            # Without test cases, score on code presence and basic structure
            score = 0.5 if code else 0.0

        return TaskScore(
            task_id=self.task_id,
            score=score,
            metadata={"code_length": len(code), "latency_ms": result.latency_ms},
        )

    def _extract_code(self, text: str) -> str:
        """Extract code from markdown code blocks."""
        patterns = [
            rf"```{self.language}\n(.*?)```",
            r"```\n(.*?)```",
            r"```(.*?)```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        # Fallback: if the entire response looks like code
        if text.strip().startswith(("def ", "class ", "import ", "from ")):
            return text.strip()
        return ""

    def _run_tests(self, code: str) -> tuple[int, int]:
        """Run test cases against generated code. Returns (passed, total)."""
        passed = 0
        total = len(self.test_cases)

        for test in self.test_cases:
            try:
                # Create isolated namespace
                namespace: dict[str, Any] = {}
                exec(code, namespace)

                # Run test assertion
                func_name = test.get("function", "")
                args = test.get("input", [])
                expected = test.get("expected")

                if func_name in namespace:
                    actual = namespace[func_name](*args) if isinstance(args, list) else namespace[func_name](args)
                    if actual == expected:
                        passed += 1
            except Exception:
                continue

        return passed, total

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, str) and len(output) > 0


class ToolUseTask(EvalTask):
    """Evaluate tool use capabilities.

    Presents a scenario requiring tool use and checks if the agent
    correctly identifies and uses the right tools.
    """

    category = "tool_use"

    def __init__(
        self,
        task_id: str,
        scenario: str = "",
        available_tools: list[dict] | None = None,
        expected_tool: str = "",
    ) -> None:
        self.task_id = task_id
        self.scenario = scenario
        self.available_tools = available_tools or []
        self.expected_tool = expected_tool
        self.description = f"Tool use: {task_id}"

    def run(self, agent: Agent) -> TaskScore:
        result = agent.generate_with_tools(self.scenario, self.available_tools)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        # Check if agent used the expected tool
        tool_calls = result.metadata.get("tool_calls", [])
        if not tool_calls:
            # Try parsing from text
            tool_calls = self._parse_tool_calls(result.text)

        score = 0.0
        if tool_calls:
            score = 0.5  # Used a tool
            if any(tc.get("name") == self.expected_tool or tc.get("tool") == self.expected_tool for tc in tool_calls):
                score = 1.0  # Used the correct tool

        return TaskScore(
            task_id=self.task_id,
            score=score,
            metadata={"tool_calls": tool_calls, "latency_ms": result.latency_ms},
        )

    def _parse_tool_calls(self, text: str) -> list[dict]:
        """Try to extract tool calls from text output."""
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "tool" in parsed:
                return [parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    def validate_output(self, output: Any) -> bool:
        return output is not None


class PlanningTask(EvalTask):
    """Evaluate planning and multi-step reasoning capabilities."""

    category = "planning"

    def __init__(
        self,
        task_id: str,
        goal: str,
        constraints: list[str] | None = None,
        expected_steps: int = 3,
    ) -> None:
        self.task_id = task_id
        self.goal = goal
        self.constraints = constraints or []
        self.expected_steps = expected_steps
        self.description = f"Planning: {task_id}"

    def run(self, agent: Agent) -> TaskScore:
        prompt = f"Create a step-by-step plan to achieve the following goal:\n\n{self.goal}"
        if self.constraints:
            prompt += f"\n\nConstraints:\n" + "\n".join(f"- {c}" for c in self.constraints)
        prompt += f"\n\nProvide at least {self.expected_steps} clear steps."

        result = agent.generate(prompt)
        if not result.success:
            return TaskScore(task_id=self.task_id, score=0.0, metadata={"error": result.error})

        score = self._score_plan(result.text)
        return TaskScore(
            task_id=self.task_id,
            score=score,
            metadata={"response_length": len(result.text), "latency_ms": result.latency_ms},
        )

    def _score_plan(self, text: str) -> float:
        if not text:
            return 0.0

        # Count numbered steps or bullet points
        step_patterns = [
            r"^\d+[\.\)]\s",  # "1. " or "1) "
            r"^[-*]\s",  # "- " or "* "
            r"^Step\s+\d+",  # "Step 1"
        ]
        lines = text.strip().split("\n")
        step_count = 0
        for line in lines:
            line = line.strip()
            if any(re.match(p, line) for p in step_patterns):
                step_count += 1

        if step_count == 0:
            return 0.2  # Wrote something but not structured

        # Score based on number of steps vs expected
        step_score = min(step_count / self.expected_steps, 1.0)

        # Check constraint mentions
        constraint_score = 0.0
        if self.constraints:
            mentioned = sum(
                1 for c in self.constraints
                if any(word.lower() in text.lower() for word in c.split()[:3])
            )
            constraint_score = mentioned / len(self.constraints)

        return 0.6 * step_score + 0.4 * constraint_score

    def validate_output(self, output: Any) -> bool:
        return isinstance(output, (str, list, dict))
