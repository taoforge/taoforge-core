"""Compound mutation combiner — multiple mutation types in one proposal."""

from __future__ import annotations

from taoforge.mutation.types import AgentState, MutationDelta, MutationType


class CompoundMutation:
    """Combines multiple mutation types into a single proposal.

    Compound mutations are higher risk/reward and require larger bond stakes.
    Maximum parts controlled by config (default: 4).
    """

    mutation_type = MutationType.COMPOUND

    def __init__(self, max_parts: int = 4) -> None:
        self.max_parts = max_parts

    def compose(self, parts: list[MutationDelta]) -> MutationDelta:
        """Compose multiple mutation deltas into a compound mutation.

        Args:
            parts: List of individual mutation deltas to combine.

        Returns:
            A compound MutationDelta containing all parts.

        Raises:
            ValueError: If parts exceed max_parts or contain nested compounds.
        """
        if len(parts) > self.max_parts:
            raise ValueError(
                f"Compound mutation has {len(parts)} parts, max is {self.max_parts}."
            )

        for part in parts:
            if part.is_compound:
                raise ValueError("Nested compound mutations are not allowed.")

        descriptions = [p.description for p in parts]
        return MutationDelta(
            mutation_type=MutationType.COMPOUND,
            description=f"Compound: {' + '.join(descriptions)}",
            compound_parts=parts,
        )

    def apply(self, agent_state: AgentState, delta: MutationDelta) -> AgentState:
        """Apply compound mutation by sequentially applying each part.

        TODO: Use MutationApplicator to dispatch each part.
        """
        if not delta.compound_parts:
            return agent_state

        current_state = agent_state
        for _part in delta.compound_parts:
            # TODO: current_state = applicator.apply(current_state, part)
            pass
        return current_state

    def validate(self, delta: MutationDelta) -> bool:
        """Validate compound mutation structure."""
        if delta.mutation_type != MutationType.COMPOUND:
            return False
        if not delta.compound_parts:
            return False
        if len(delta.compound_parts) > self.max_parts:
            return False
        return all(not p.is_compound for p in delta.compound_parts)
