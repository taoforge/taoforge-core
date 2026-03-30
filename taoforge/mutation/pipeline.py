"""Inference pipeline mutations."""

from __future__ import annotations

from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class InferencePipelineMutation:
    """Handles inference pipeline mutations.

    Operations: modify batching strategy, adjust decoding parameters,
    change sampling config, optimize throughput/latency tradeoffs.
    """

    mutation_type = MutationType.INFERENCE_PIPELINE

    def propose(self, agent_state: AgentState) -> MutationDelta:
        """Propose an inference pipeline change based on current state."""
        return MutationDelta(
            mutation_type=self.mutation_type,
            description="Inference pipeline change — stub",
            parent_hash=agent_state.weights_hash,
        )

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply pipeline changes to the agent state."""
        new_state = AgentState(
            agent_id=agent_state.agent_id,
            weights_hash=agent_state.weights_hash,
            tool_graph=agent_state.tool_graph,
            prompt_chain=agent_state.prompt_chain,
            memory_config=agent_state.memory_config,
            pipeline_config=delta.parameters.get(
                "new_pipeline_config", agent_state.pipeline_config
            ),
        )
        return new_state

    def validate(self, delta: MutationDelta) -> bool:
        if delta.mutation_type != self.mutation_type:
            return False
        return len(delta.validate()) == 0
