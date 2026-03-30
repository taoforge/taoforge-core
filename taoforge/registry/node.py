"""DAG node — represents a single verified improvement in the registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DAGNode:
    """A node in the improvement DAG.

    Each node represents a verified improvement delta with parent lineage,
    enabling evolutionary tree visualization.
    """

    node_id: str = ""
    agent_id: str = ""
    parent_id: Optional[str] = None
    mutation_type: str = ""
    improvement_delta: float = 0.0
    benchmark_id: str = ""
    timestamp: float = 0.0
    proof_hash: str = ""
    reputation_at_time: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def is_root(self) -> bool:
        """Whether this is a root node (no parent)."""
        return self.parent_id is None

    @property
    def depth(self) -> int:
        """Placeholder — actual depth requires DAG traversal."""
        return 0
