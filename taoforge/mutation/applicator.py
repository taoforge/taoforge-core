"""Mutation applicator — dispatches mutations to type-specific handlers."""

from __future__ import annotations

from taoforge.mutation.lora import LoRAMutation
from taoforge.mutation.memory_index import MemoryIndexMutation
from taoforge.mutation.pipeline import InferencePipelineMutation
from taoforge.mutation.prompt_chain import PromptChainMutation
from taoforge.mutation.tool_graph import ToolGraphMutation
from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class MutationApplicator:
    """Dispatches mutation deltas to the correct type-specific handler.

    Routes based on MutationType and applies the mutation to the agent state.
    """

    def __init__(self) -> None:
        self._handlers = {
            MutationType.LORA_MERGE: LoRAMutation(),
            MutationType.TOOL_GRAPH_REWIRE: ToolGraphMutation(),
            MutationType.PROMPT_CHAIN_REFACTOR: PromptChainMutation(),
            MutationType.MEMORY_INDEX_REBUILD: MemoryIndexMutation(),
            MutationType.INFERENCE_PIPELINE: InferencePipelineMutation(),
        }

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply a mutation delta to an agent state.

        For compound mutations, applies each part sequentially.

        Args:
            agent_state: Current agent state.
            delta: The mutation to apply.

        Returns:
            New agent state after mutation.

        Raises:
            ValueError: If mutation type is unsupported.
        """
        if delta.is_compound:
            return self._apply_compound(agent_state, delta)

        handler = self._handlers.get(delta.mutation_type)
        if handler is None:
            raise ValueError(f"No handler for mutation type: {delta.mutation_type}")

        return handler.apply(agent_state, delta)

    def _apply_compound(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply a compound mutation by sequentially applying each part."""
        if not delta.compound_parts:
            return agent_state

        current = agent_state
        for part in delta.compound_parts:
            current = self.apply(current, part)
        return current

    def validate(self, delta: MutationDelta) -> bool:
        """Validate a mutation delta via its type-specific handler."""
        if delta.is_compound:
            if not delta.compound_parts:
                return False
            return all(self.validate(p) for p in delta.compound_parts)

        handler = self._handlers.get(delta.mutation_type)
        if handler is None:
            return False
        return handler.validate(delta)
