"""API-based agent — wraps external LLM APIs (OpenAI, Anthropic, etc.)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from taoforge.agent.base import Agent, AgentConfig, GenerationResult

logger = logging.getLogger(__name__)


class APIAgent(Agent):
    """Agent backed by an external LLM API.

    Mutations modify prompt chains, tool configs, and routing — not weights.
    Supports OpenAI and Anthropic APIs.
    """

    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self._client = None

    def load(self) -> None:
        """Initialize the API client."""
        provider = self.config.api_provider.lower()

        if provider == "openai":
            self._load_openai()
        elif provider == "anthropic":
            self._load_anthropic()
        else:
            raise ValueError(f"Unsupported API provider: {provider}")

        self._loaded = True
        logger.info(
            f"API agent loaded | provider={provider} | model={self.config.api_model}"
        )

    def _load_openai(self) -> None:
        try:
            import os
            from openai import OpenAI
            kwargs: dict[str, Any] = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            # Resolve base URL: config takes priority, then OPENAI_BASE_URL, then OPENAI_API_BASE
            base_url = (
                self.config.api_base_url
                or os.environ.get("OPENAI_BASE_URL")
                or os.environ.get("OPENAI_API_BASE")
            )
            if base_url:
                kwargs["base_url"] = base_url
            kwargs["timeout"] = 120.0  # 2 min max per request — fail fast if tunnel drops
            self._client = OpenAI(**kwargs)
        except ImportError:
            raise RuntimeError("openai package not installed. pip install openai")

    def _load_anthropic(self) -> None:
        try:
            from anthropic import Anthropic
            kwargs: dict[str, Any] = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            self._client = Anthropic(**kwargs)
        except ImportError:
            raise RuntimeError("anthropic package not installed. pip install anthropic")

    def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Generate via the API."""
        if not self._loaded:
            raise RuntimeError("Agent not loaded. Call agent.load() first.")

        start = time.monotonic()
        provider = self.config.api_provider.lower()

        try:
            if provider == "openai":
                return self._generate_openai(prompt, start, **kwargs)
            elif provider == "anthropic":
                return self._generate_anthropic(prompt, start, **kwargs)
            else:
                return GenerationResult(error=f"Unknown provider: {provider}")
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(f"API generation error: {e}")
            return GenerationResult(error=str(e), latency_ms=elapsed_ms)

    def _generate_openai(self, prompt: str, start: float, **kwargs: Any) -> GenerationResult:
        messages = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        formatted = self.config.prompt_template.replace("{input}", prompt)
        messages.append({"role": "user", "content": formatted})

        response = self._client.chat.completions.create(
            model=self.config.api_model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return GenerationResult(text=text, tokens_used=tokens, latency_ms=elapsed_ms)

    def _generate_anthropic(self, prompt: str, start: float, **kwargs: Any) -> GenerationResult:
        formatted = self.config.prompt_template.replace("{input}", prompt)

        msg_kwargs: dict[str, Any] = {
            "model": self.config.api_model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": [{"role": "user", "content": formatted}],
        }
        if self.config.system_prompt:
            msg_kwargs["system"] = self.config.system_prompt

        response = self._client.messages.create(**msg_kwargs)

        elapsed_ms = (time.monotonic() - start) * 1000
        text = response.content[0].text if response.content else ""
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return GenerationResult(text=text, tokens_used=tokens, latency_ms=elapsed_ms)

    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate with tool use via the API's native tool support."""
        if not self._loaded:
            raise RuntimeError("Agent not loaded.")

        provider = self.config.api_provider.lower()
        start = time.monotonic()

        try:
            if provider == "openai":
                return self._generate_openai_tools(prompt, tools, start, **kwargs)
            else:
                # Fallback: embed tool descriptions in prompt
                return self.generate(
                    f"Tools available: {json.dumps(tools)}\n\n{prompt}", **kwargs
                )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            return GenerationResult(error=str(e), latency_ms=elapsed_ms)

    def _generate_openai_tools(
        self, prompt: str, tools: list[dict], start: float, **kwargs: Any
    ) -> GenerationResult:
        messages = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.config.api_model,
            messages=messages,
            tools=tools,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        choice = response.choices[0]
        text = choice.message.content or ""
        metadata = {}
        if choice.message.tool_calls:
            metadata["tool_calls"] = [
                {"name": tc.function.name, "args": tc.function.arguments}
                for tc in choice.message.tool_calls
            ]

        return GenerationResult(
            text=text,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=elapsed_ms,
            metadata=metadata,
        )

    def get_state_hash(self) -> str:
        """Hash the agent's configuration (since API agents have no local weights)."""
        hasher = hashlib.sha256()
        hasher.update(self.config.api_provider.encode())
        hasher.update(self.config.api_model.encode())
        hasher.update(self.config.system_prompt.encode())
        hasher.update(self.config.prompt_template.encode())
        hasher.update(json.dumps(self.config.tools, sort_keys=True).encode())
        return hasher.hexdigest()

    def save_checkpoint(self, path: str) -> None:
        """Save the agent config (API agents are stateless aside from config)."""
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)
        with open(save_path / "agent_config.json", "w") as f:
            json.dump({
                "runtime": "api",
                "api_provider": self.config.api_provider,
                "api_model": self.config.api_model,
                "system_prompt": self.config.system_prompt,
                "prompt_template": self.config.prompt_template,
                "tools": self.config.tools,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }, f, indent=2)

    def load_checkpoint(self, path: str) -> None:
        """Load agent config from checkpoint."""
        config_path = Path(path) / "agent_config.json"
        if config_path.exists():
            with open(config_path) as f:
                saved = json.load(f)
            self.config.api_provider = saved.get("api_provider", self.config.api_provider)
            self.config.api_model = saved.get("api_model", self.config.api_model)
            self.config.system_prompt = saved.get("system_prompt", "")
            self.config.prompt_template = saved.get("prompt_template", "{input}")
            self.config.tools = saved.get("tools", [])
        self.load()

    def update_prompt_chain(
        self,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> None:
        """Update the prompt chain (primary mutation vector for API agents)."""
        if system_prompt is not None:
            self.config.system_prompt = system_prompt
        if prompt_template is not None:
            self.config.prompt_template = prompt_template
        logger.info("API agent prompt chain updated.")

    def update_tools(self, tools: list[dict]) -> None:
        """Update the tool definitions (tool graph mutation for API agents)."""
        self.config.tools = tools
        logger.info(f"API agent tools updated: {len(tools)} tools configured.")
