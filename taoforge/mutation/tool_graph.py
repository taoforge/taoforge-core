"""Tool graph rewiring mutations."""

from __future__ import annotations

from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class ToolGraphMutation:
    """Handles tool graph rewiring mutations.

    Operations: add/remove tools, reorder execution, rewire connections
    between tool nodes, adjust routing logic.
    """

    mutation_type = MutationType.TOOL_GRAPH_REWIRE

    def propose(self, agent_state: AgentState) -> MutationDelta:
        """Propose a tool graph rewiring based on current state."""
        return MutationDelta(
            mutation_type=self.mutation_type,
            description="Tool graph rewiring — stub",
            parent_hash=agent_state.weights_hash,
        )

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply tool graph rewiring to the agent state."""
        new_state = AgentState(
            agent_id=agent_state.agent_id,
            weights_hash=agent_state.weights_hash,
            tool_graph=delta.parameters.get("new_tool_graph", agent_state.tool_graph),
            prompt_chain=agent_state.prompt_chain,
            memory_config=agent_state.memory_config,
            pipeline_config=agent_state.pipeline_config,
        )
        return new_state

    def validate(self, delta: MutationDelta) -> bool:
        if delta.mutation_type != self.mutation_type:
            return False
        return len(delta.validate()) == 0
