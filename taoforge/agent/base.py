"""Base Agent interface — the contract all TaoForge agents must implement."""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for creating an agent."""

    # Identity
    agent_id: str = ""
    name: str = ""

    # Runtime type
    runtime: str = "local_llm"  # "local_llm" | "api" | "custom"

    # Local LLM settings
    model_name_or_path: str = ""  # HuggingFace model ID or local path
    adapter_path: Optional[str] = None  # LoRA adapter path
    device: str = "auto"
    dtype: str = "auto"  # "float16", "bfloat16", "float32", "auto"
    max_memory: Optional[dict[str, str]] = None  # device_map memory limits

    # API settings
    api_provider: str = ""  # "openai" | "anthropic" | "custom"
    api_key: str = ""
    api_model: str = ""  # e.g., "gpt-4", "claude-sonnet-4-20250514"
    api_base_url: str = ""

    # Generation defaults
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9

    # Prompt chain
    system_prompt: str = ""
    prompt_template: str = "{input}"
    tools: list[dict] = field(default_factory=list)

    # Memory
    memory_backend: str = "none"  # "none" | "chromadb" | "faiss"
    memory_config: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of a single agent generation call."""

    text: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.text) > 0


class Agent(abc.ABC):
    """Base interface for all TaoForge agents.

    An agent wraps a model (local or API) and provides a uniform
    interface for generation, evaluation, and mutation.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._loaded = False

    @abc.abstractmethod
    def load(self) -> None:
        """Load the agent's model/resources into memory.

        Called once before first use. Implementations should set self._loaded = True.
        """
        ...

    @abc.abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Generate a response to a prompt.

        This is the core method all evaluation tasks call.

        Args:
            prompt: The input prompt/question.
            **kwargs: Override generation params (max_tokens, temperature, etc.)

        Returns:
            GenerationResult with the agent's response.
        """
        ...

    @abc.abstractmethod
    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a response with tool use capabilities.

        Args:
            prompt: The input prompt.
            tools: Available tool definitions.
            **kwargs: Override generation params.

        Returns:
            GenerationResult, potentially including tool calls in metadata.
        """
        ...

    def batch_generate(
        self,
        prompts: list[str],
        **kwargs: Any,
    ) -> list[GenerationResult]:
        """Generate responses for multiple prompts.

        Default: sequential. Override for batched/parallel execution.
        """
        return [self.generate(p, **kwargs) for p in prompts]

    @abc.abstractmethod
    def get_state_hash(self) -> str:
        """Return a hash representing the agent's current state.

        Used for ZK proof commitments. Must change when the agent is mutated.
        """
        ...

    @abc.abstractmethod
    def save_checkpoint(self, path: str) -> None:
        """Save the agent's full state to disk."""
        ...

    @abc.abstractmethod
    def load_checkpoint(self, path: str) -> None:
        """Load the agent's state from a checkpoint."""
        ...

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, runtime={self.config.runtime})"
