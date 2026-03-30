"""Improvement DAG — directed acyclic graph of verified improvements."""

from __future__ import annotations

from typing import Optional

from taoforge.registry.node import DAGNode


class ImprovementDAG:
    """In-memory representation of the on-chain improvement DAG.

    The DAG tracks the evolutionary history of all verified agent improvements.
    Each node is a verified improvement with parent lineage.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}
        self._children: dict[str, list[str]] = {}  # parent_id -> [child_ids]
        self._agent_nodes: dict[str, list[str]] = {}  # agent_id -> [node_ids]

    def add_node(self, node: DAGNode) -> None:
        """Add a verified improvement node to the DAG."""
        self._nodes[node.node_id] = node

        # Track children
        if node.parent_id:
            self._children.setdefault(node.parent_id, []).append(node.node_id)

        # Track per-agent history
        self._agent_nodes.setdefault(node.agent_id, []).append(node.node_id)

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> list[DAGNode]:
        """Get all direct children of a node."""
        child_ids = self._children.get(node_id, [])
        return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def get_lineage(self, node_id: str) -> list[DAGNode]:
        """Get the full ancestry chain from a node back to its root."""
        lineage = []
        current = node_id
        visited = set()

        while current and current not in visited:
            visited.add(current)
            node = self._nodes.get(current)
            if node is None:
                break
            lineage.append(node)
            current = node.parent_id

        return lineage

    def get_agent_history(self, agent_id: str) -> list[DAGNode]:
        """Get all improvement nodes for a specific agent, ordered by timestamp."""
        node_ids = self._agent_nodes.get(agent_id, [])
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
        return sorted(nodes, key=lambda n: n.timestamp)

    def get_frontier(self) -> list[DAGNode]:
        """Get leaf nodes (current best agents with no further improvements)."""
        all_parents = set()
        for node in self._nodes.values():
            if node.parent_id:
                all_parents.add(node.parent_id)

        return [
            node for nid, node in self._nodes.items()
            if nid not in all_parents
        ]

    def get_roots(self) -> list[DAGNode]:
        """Get all root nodes (initial agent registrations)."""
        return [node for node in self._nodes.values() if node.is_root]

    @property
    def size(self) -> int:
        return len(self._nodes)

    @property
    def agent_count(self) -> int:
        return len(self._agent_nodes)

    @property
    def max_depth(self) -> int:
        """Maximum depth of the DAG (longest lineage chain)."""
        if not self._nodes:
            return 0
        max_d = 0
        for node_id in self._nodes:
            max_d = max(max_d, len(self.get_lineage(node_id)))
        return max_d
