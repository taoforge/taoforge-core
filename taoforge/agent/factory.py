"""Agent factory — create agents from config, model name, or API settings."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from taoforge.agent.base import Agent, AgentConfig

logger = logging.getLogger(__name__)


def create_agent(config: AgentConfig) -> Agent:
    """Create an agent from a configuration.

    Args:
        config: Agent configuration specifying runtime, model, etc.

    Returns:
        An Agent instance (not yet loaded — call agent.load()).

    Raises:
        ValueError: If runtime type is unsupported.
    """
    if not config.agent_id:
        config.agent_id = str(uuid.uuid4())[:8]

    runtime = config.runtime.lower()

    if runtime == "local_llm":
        from taoforge.agent.local_llm import LocalLLMAgent
        return LocalLLMAgent(config)

    elif runtime == "api":
        from taoforge.agent.api_agent import APIAgent
        return APIAgent(config)

    else:
        raise ValueError(
            f"Unknown runtime: {runtime}. Supported: 'local_llm', 'api'"
        )


def create_local_agent(
    model: str,
    adapter: Optional[str] = None,
    system_prompt: str = "",
    device: str = "auto",
    dtype: str = "auto",
) -> Agent:
    """Shortcut to create a local LLM agent.

    Args:
        model: HuggingFace model ID or local path (e.g., "microsoft/phi-3-mini-4k-instruct").
        adapter: Optional LoRA adapter path.
        system_prompt: System prompt for the agent.
        device: Device to load on ("auto", "cuda", "cpu").
        dtype: Dtype ("float16", "bfloat16", "auto").

    Returns:
        A LocalLLMAgent (call .load() to initialize).
    """
    config = AgentConfig(
        runtime="local_llm",
        model_name_or_path=model,
        adapter_path=adapter,
        system_prompt=system_prompt,
        device=device,
        dtype=dtype,
    )
    return create_agent(config)


def create_api_agent(
    provider: str,
    model: str,
    api_key: str = "",
    system_prompt: str = "",
) -> Agent:
    """Shortcut to create an API-based agent.

    Args:
        provider: "openai" or "anthropic".
        model: Model name (e.g., "gpt-4", "claude-sonnet-4-20250514").
        api_key: API key (or set via environment variable).
        system_prompt: System prompt for the agent.

    Returns:
        An APIAgent (call .load() to initialize).
    """
    config = AgentConfig(
        runtime="api",
        api_provider=provider,
        api_model=model,
        api_key=api_key,
        system_prompt=system_prompt,
    )
    return create_agent(config)
