"""Memory index rebuild mutations."""

from __future__ import annotations

from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class MemoryIndexMutation:
    """Handles memory index rebuild mutations.

    Operations: change embedding model, adjust chunk size/overlap,
    rebuild retrieval strategy, restructure index topology.
    """

    mutation_type = MutationType.MEMORY_INDEX_REBUILD

    def propose(self, agent_state: AgentState) -> MutationDelta:
        """Propose a memory index rebuild based on current state."""
        return MutationDelta(
            mutation_type=self.mutation_type,
            description="Memory index rebuild — stub",
            parent_hash=agent_state.weights_hash,
        )

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply memory index changes to the agent state."""
        new_state = AgentState(
            agent_id=agent_state.agent_id,
            weights_hash=agent_state.weights_hash,
            tool_graph=agent_state.tool_graph,
            prompt_chain=agent_state.prompt_chain,
            memory_config=delta.parameters.get("new_memory_config", agent_state.memory_config),
            pipeline_config=agent_state.pipeline_config,
        )
        return new_state

    def validate(self, delta: MutationDelta) -> bool:
        if delta.mutation_type != self.mutation_type:
            return False
        return len(delta.validate()) == 0
