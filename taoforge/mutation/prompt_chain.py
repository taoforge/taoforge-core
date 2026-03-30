"""Prompt chain refactor mutations."""

from __future__ import annotations

from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class PromptChainMutation:
    """Handles prompt chain refactor mutations.

    Operations: insert/remove/reorder prompt steps, modify templates,
    adjust chain-of-thought structure, optimize system prompts.
    """

    mutation_type = MutationType.PROMPT_CHAIN_REFACTOR

    def propose(self, agent_state: AgentState) -> MutationDelta:
        """Propose a prompt chain refactor based on current state."""
        return MutationDelta(
            mutation_type=self.mutation_type,
            description="Prompt chain refactor — stub",
            parent_hash=agent_state.weights_hash,
        )

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply prompt chain changes to the agent state."""
        new_state = AgentState(
            agent_id=agent_state.agent_id,
            weights_hash=agent_state.weights_hash,
            tool_graph=agent_state.tool_graph,
            prompt_chain=delta.parameters.get("new_prompt_chain", agent_state.prompt_chain),
            memory_config=agent_state.memory_config,
            pipeline_config=agent_state.pipeline_config,
        )
        return new_state

    def validate(self, delta: MutationDelta) -> bool:
        if delta.mutation_type != self.mutation_type:
            return False
        return len(delta.validate()) == 0
