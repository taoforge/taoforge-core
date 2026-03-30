"""Lineage verification — ensures proposals have legitimate ancestry."""

from __future__ import annotations

from taoforge.proposal.schema import ImprovementProposal
from taoforge.registry.dag import ImprovementDAG


class LineageVerifier:
    """Verifies that a proposal's claimed parent lineage is legitimate.

    Prevents agents from claiming false ancestry (e.g., fresh models
    pretending to be improvements of existing agents).
    """

    def __init__(self, dag: ImprovementDAG) -> None:
        self.dag = dag

    def verify_lineage(self, proposal: ImprovementProposal) -> bool:
        """Verify that the proposal's parent_delta exists and belongs to the same agent.

        Args:
            proposal: The proposal to verify.

        Returns:
            True if lineage is valid.
        """
        # Root proposals (no parent) are always valid
        if proposal.parent_delta is None:
            return True

        parent_node = self.dag.get_node(proposal.parent_delta)
        if parent_node is None:
            return False

        # Parent must belong to the same agent
        if parent_node.agent_id != proposal.agent_id:
            return False

        return True

    def detect_fabricated_ancestry(self, proposal: ImprovementProposal) -> bool:
        """Detect if a proposal has fabricated its ancestry.

        Checks for suspicious patterns like:
        - Claiming a parent that doesn't exist
        - Claiming a parent from a different agent
        - Claiming lineage with impossible timestamp ordering

        Returns:
            True if ancestry appears fabricated.
        """
        if proposal.parent_delta is None:
            return False

        parent = self.dag.get_node(proposal.parent_delta)
        if parent is None:
            return True  # Nonexistent parent

        if parent.agent_id != proposal.agent_id:
            return True  # Wrong agent

        if proposal.timestamp < parent.timestamp:
            return True  # Impossible: child before parent

        # TODO: Verify ZK proof of lineage
        return False
