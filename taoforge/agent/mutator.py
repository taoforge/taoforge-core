"""Agent mutator — applies abstract mutation deltas to real agents."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from taoforge.agent.base import Agent, AgentConfig
from taoforge.mutation.types import AgentState, MutationDelta, MutationType

logger = logging.getLogger(__name__)


class AgentMutator:
    """Connects the abstract mutation framework to real agent operations.

    When a MutationDelta is applied, this class knows how to translate
    it into actual changes on the agent (merge LoRA, update prompts, etc.)
    """

    def apply_mutation(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Apply a mutation to an agent.

        Args:
            agent: The agent to mutate.
            delta: The mutation to apply.

        Returns:
            The mutated agent (may be the same object, modified in place).
        """
        mt = delta.mutation_type

        if mt == MutationType.LORA_MERGE:
            return self._apply_lora(agent, delta)
        elif mt == MutationType.PROMPT_CHAIN_REFACTOR:
            return self._apply_prompt_chain(agent, delta)
        elif mt == MutationType.TOOL_GRAPH_REWIRE:
            return self._apply_tool_graph(agent, delta)
        elif mt == MutationType.MEMORY_INDEX_REBUILD:
            return self._apply_memory_rebuild(agent, delta)
        elif mt == MutationType.INFERENCE_PIPELINE:
            return self._apply_pipeline(agent, delta)
        elif mt == MutationType.COMPOUND:
            return self._apply_compound(agent, delta)
        else:
            logger.warning(f"Unknown mutation type: {mt}")
            return agent

    def _apply_lora(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Merge a LoRA adapter onto the agent's model."""
        adapter_path = delta.parameters.get("adapter_path", "")
        if not adapter_path:
            logger.warning("LoRA mutation has no adapter_path parameter.")
            return agent

        if hasattr(agent, "merge_adapter"):
            agent.merge_adapter(adapter_path)
            logger.info(f"LoRA adapter merged: {adapter_path}")
        else:
            logger.warning(f"Agent {agent} does not support adapter merging.")

        return agent

    def _apply_prompt_chain(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Update the agent's prompt chain."""
        new_system = delta.parameters.get("system_prompt")
        new_template = delta.parameters.get("prompt_template")

        if hasattr(agent, "update_prompt_chain"):
            agent.update_prompt_chain(
                system_prompt=new_system,
                prompt_template=new_template,
            )
        else:
            if new_system is not None:
                agent.config.system_prompt = new_system
            if new_template is not None:
                agent.config.prompt_template = new_template

        logger.info("Prompt chain mutation applied.")
        return agent

    def _apply_tool_graph(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Update the agent's tool configuration."""
        new_tools = delta.parameters.get("tools")
        if new_tools is not None:
            if hasattr(agent, "update_tools"):
                agent.update_tools(new_tools)
            else:
                agent.config.tools = new_tools
            logger.info(f"Tool graph updated: {len(new_tools)} tools configured.")
        return agent

    def _apply_memory_rebuild(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Rebuild the agent's memory/retrieval configuration."""
        new_config = delta.parameters.get("memory_config", {})
        agent.config.memory_config.update(new_config)
        agent.config.memory_backend = delta.parameters.get(
            "memory_backend", agent.config.memory_backend
        )
        logger.info("Memory index configuration updated.")
        return agent

    def _apply_pipeline(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Update inference pipeline settings."""
        if "temperature" in delta.parameters:
            agent.config.temperature = delta.parameters["temperature"]
        if "top_p" in delta.parameters:
            agent.config.top_p = delta.parameters["top_p"]
        if "max_tokens" in delta.parameters:
            agent.config.max_tokens = delta.parameters["max_tokens"]
        logger.info("Inference pipeline settings updated.")
        return agent

    def _apply_compound(self, agent: Agent, delta: MutationDelta) -> Agent:
        """Apply compound mutation by sequentially applying each part."""
        if not delta.compound_parts:
            return agent
        for part in delta.compound_parts:
            agent = self.apply_mutation(agent, part)
        return agent

    @staticmethod
    def agent_to_state(agent: Agent) -> AgentState:
        """Extract an AgentState from a live agent (for the abstract framework)."""
        return AgentState(
            agent_id=agent.config.agent_id,
            weights_hash=agent.get_state_hash(),
            tool_graph={"tools": agent.config.tools},
            prompt_chain=[agent.config.system_prompt, agent.config.prompt_template],
            memory_config=agent.config.memory_config,
            pipeline_config={
                "temperature": agent.config.temperature,
                "top_p": agent.config.top_p,
                "max_tokens": agent.config.max_tokens,
            },
        )
