"""Local LLM agent — wraps HuggingFace transformers + PEFT for local inference."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from taoforge.agent.base import Agent, AgentConfig, GenerationResult

logger = logging.getLogger(__name__)


class LocalLLMAgent(Agent):
    """Agent backed by a local LLM via HuggingFace transformers.

    Supports LoRA adapters via PEFT for efficient fine-tuning/mutation.
    """

    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self._model = None
        self._tokenizer = None
        self._generation_config = None

    def load(self) -> None:
        """Load the model and tokenizer into memory."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(
                f"Loading model: {self.config.model_name_or_path} | "
                f"device={self.config.device} | dtype={self.config.dtype}"
            )

            # Resolve dtype
            dtype_map = {
                "float16": torch.float16,
                "bfloat16": torch.bfloat16,
                "float32": torch.float32,
                "auto": "auto",
            }
            dtype = dtype_map.get(self.config.dtype, "auto")

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name_or_path,
                trust_remote_code=True,
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            # Load model
            load_kwargs: dict[str, Any] = {
                "trust_remote_code": True,
            }
            if dtype != "auto":
                load_kwargs["torch_dtype"] = dtype
            if self.config.device == "auto":
                load_kwargs["device_map"] = "auto"
            if self.config.max_memory:
                load_kwargs["max_memory"] = self.config.max_memory

            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name_or_path,
                **load_kwargs,
            )

            # Load LoRA adapter if specified
            if self.config.adapter_path:
                self._load_adapter(self.config.adapter_path)

            # Move to device if not auto
            if self.config.device not in ("auto", "cpu") and hasattr(self._model, "to"):
                self._model.to(self.config.device)

            self._model.eval()
            self._loaded = True

            param_count = sum(p.numel() for p in self._model.parameters())
            logger.info(
                f"Model loaded | params={param_count/1e9:.1f}B | "
                f"device={next(self._model.parameters()).device}"
            )

        except ImportError as e:
            raise RuntimeError(
                f"Missing dependency for local LLM: {e}. "
                "Install with: pip install transformers torch"
            ) from e

    def _load_adapter(self, adapter_path: str) -> None:
        """Load a PEFT LoRA adapter onto the base model."""
        try:
            from peft import PeftModel

            logger.info(f"Loading LoRA adapter: {adapter_path}")
            self._model = PeftModel.from_pretrained(self._model, adapter_path)
            logger.info("LoRA adapter loaded successfully.")
        except ImportError:
            logger.warning("peft not installed — skipping adapter load.")

    def generate(self, prompt: str, **kwargs: Any) -> GenerationResult:
        """Generate a response using the local LLM."""
        if not self._loaded:
            raise RuntimeError("Agent not loaded. Call agent.load() first.")

        import torch

        start = time.monotonic()

        try:
            # Format prompt
            full_prompt = self._format_prompt(prompt)

            # Tokenize
            inputs = self._tokenizer(
                full_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=4096,
            ).to(self._model.device)

            # Generate
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            temperature = kwargs.get("temperature", self.config.temperature)
            top_p = kwargs.get("top_p", self.config.top_p)

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature if temperature > 0 else None,
                    top_p=top_p,
                    do_sample=temperature > 0,
                    pad_token_id=self._tokenizer.pad_token_id,
                )

            # Decode only the generated tokens (skip input)
            generated = outputs[0][inputs["input_ids"].shape[1]:]
            text = self._tokenizer.decode(generated, skip_special_tokens=True)

            elapsed_ms = (time.monotonic() - start) * 1000

            return GenerationResult(
                text=text.strip(),
                tokens_used=len(generated),
                latency_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(f"Generation error: {e}")
            return GenerationResult(error=str(e), latency_ms=elapsed_ms)

    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate with tool-use instructions embedded in the prompt."""
        tool_descriptions = json.dumps(tools, indent=2)
        augmented_prompt = (
            f"You have access to the following tools:\n{tool_descriptions}\n\n"
            f"To use a tool, respond with a JSON object: "
            f'{{"tool": "tool_name", "args": {{...}}}}\n\n'
            f"{prompt}"
        )
        result = self.generate(augmented_prompt, **kwargs)

        # Try to parse tool calls from output
        if result.success:
            try:
                parsed = json.loads(result.text)
                if "tool" in parsed:
                    result.metadata["tool_call"] = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        return result

    def get_state_hash(self) -> str:
        """Hash the model's current parameter state."""
        if not self._loaded:
            return hashlib.sha256(self.config.model_name_or_path.encode()).hexdigest()

        import torch

        # Hash a sample of parameters for efficiency
        hasher = hashlib.sha256()
        hasher.update(self.config.model_name_or_path.encode())
        if self.config.adapter_path:
            hasher.update(self.config.adapter_path.encode())

        # Include a fingerprint from actual weights
        for name, param in list(self._model.named_parameters())[:10]:
            hasher.update(name.encode())
            hasher.update(param.data.cpu().float().numpy().tobytes()[:64])

        return hasher.hexdigest()

    def save_checkpoint(self, path: str) -> None:
        """Save model + adapter state."""
        if not self._loaded:
            return
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)
        self._model.save_pretrained(str(save_path / "model"))
        self._tokenizer.save_pretrained(str(save_path / "tokenizer"))
        # Save config
        with open(save_path / "agent_config.json", "w") as f:
            json.dump({
                "model_name_or_path": self.config.model_name_or_path,
                "adapter_path": self.config.adapter_path,
                "system_prompt": self.config.system_prompt,
                "prompt_template": self.config.prompt_template,
                "temperature": self.config.temperature,
            }, f, indent=2)

    def load_checkpoint(self, path: str) -> None:
        """Load model from a checkpoint directory."""
        save_path = Path(path)
        config_path = save_path / "agent_config.json"
        if config_path.exists():
            with open(config_path) as f:
                saved = json.load(f)
            self.config.model_name_or_path = str(save_path / "model")
            self.config.system_prompt = saved.get("system_prompt", "")
            self.config.prompt_template = saved.get("prompt_template", "{input}")
        self.load()

    def _format_prompt(self, user_input: str) -> str:
        """Format the prompt using system prompt and template."""
        formatted = self.config.prompt_template.replace("{input}", user_input)
        if self.config.system_prompt:
            # Use chat template if available
            if hasattr(self._tokenizer, "apply_chat_template"):
                messages = [
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": formatted},
                ]
                try:
                    return self._tokenizer.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
                except Exception:
                    pass
            return f"{self.config.system_prompt}\n\n{formatted}"
        return formatted

    def merge_adapter(self, adapter_path: str) -> None:
        """Merge a new LoRA adapter into the model (for mutations)."""
        if not self._loaded:
            raise RuntimeError("Model not loaded.")
        self._load_adapter(adapter_path)
        self.config.adapter_path = adapter_path
        logger.info(f"Adapter merged: {adapter_path}")

    def update_prompt_chain(
        self,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> None:
        """Update the prompt chain (for prompt mutations)."""
        if system_prompt is not None:
            self.config.system_prompt = system_prompt
        if prompt_template is not None:
            self.config.prompt_template = prompt_template
        logger.info("Prompt chain updated.")
