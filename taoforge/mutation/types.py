"""Mutation type definitions and core data structures."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class MutationType(enum.Enum):
    """Types of self-improvement mutations an agent can propose."""

    LORA_MERGE = "lora_merge"
    TOOL_GRAPH_REWIRE = "tool_graph_rewire"
    PROMPT_CHAIN_REFACTOR = "prompt_chain_refactor"
    MEMORY_INDEX_REBUILD = "memory_index_rebuild"
    INFERENCE_PIPELINE = "inference_pipeline"
    SUBNET_SWITCH = "subnet_switch"
    COMPOUND = "compound"


@dataclass
class MutationDelta:
    """Describes a mutation applied to an agent.

    The delta is the diff between the agent's pre- and post-mutation state.
    """

    mutation_type: MutationType
    description: str = ""
    diff_hash: str = ""  # Hash of the actual diff payload
    parent_hash: Optional[str] = None  # Hash of the pre-mutation agent state
    compound_parts: Optional[list[MutationDelta]] = None  # For compound mutations
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def is_compound(self) -> bool:
        return self.mutation_type == MutationType.COMPOUND

    def validate(self) -> list[str]:
        """Basic structural validation. Returns list of errors."""
        errors = []
        if not self.description:
            errors.append("Mutation delta must have a description.")
        if self.is_compound and not self.compound_parts:
            errors.append("Compound mutation must have compound_parts.")
        if self.is_compound and self.compound_parts:
            for part in self.compound_parts:
                if part.is_compound:
                    errors.append("Nested compound mutations are not allowed.")
        return errors


@dataclass
class AgentState:
    """Represents the current state of an agent for mutation purposes."""

    agent_id: str = ""
    weights_hash: str = ""
    tool_graph: dict = field(default_factory=dict)
    prompt_chain: list[str] = field(default_factory=list)
    memory_config: dict = field(default_factory=dict)
    pipeline_config: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
