"""Registry client — interface to the improvement registry."""

from __future__ import annotations

import logging

from taoforge.proposal.schema import ImprovementProposal
from taoforge.registry.dag import ImprovementDAG
from taoforge.registry.node import DAGNode

logger = logging.getLogger(__name__)


class RegistryClient:
    """Interface to the improvement DAG.

    Handles reading and writing improvement records.
    Can be backed by local storage, a database, or a distributed ledger.
    """

    def __init__(self) -> None:
        self._local_dag = ImprovementDAG()

    def register_improvement(
        self,
        proposal: ImprovementProposal,
        verified_score: float,
        reputation: float,
    ) -> DAGNode:
        """Register a verified improvement.

        Args:
            proposal: The accepted improvement proposal.
            verified_score: Validator-verified improvement magnitude.
            reputation: Agent's current reputation score.

        Returns:
            The created DAG node.
        """
        node = DAGNode(
            node_id=proposal.proposal_id,
            agent_id=proposal.agent_id,
            parent_id=proposal.parent_delta,
            mutation_type=proposal.mutation_type,
            improvement_delta=verified_score,
            benchmark_id=(
                proposal.baseline_proof.benchmark_id
                if proposal.baseline_proof
                else ""
            ),
            proof_hash=(
                proposal.delta_proof.score_hash
                if proposal.delta_proof
                else ""
            ),
            reputation_at_time=reputation,
        )

        self._local_dag.add_node(node)

        logger.info(
            f"Improvement registered | node={node.node_id} | "
            f"agent={node.agent_id[:16]}... | delta={verified_score:.4f}"
        )

        return node

    def query_agent_history(self, agent_id: str) -> list[DAGNode]:
        """Query an agent's improvement history."""
        return self._local_dag.get_agent_history(agent_id)

    def query_dag_root(self) -> list[DAGNode]:
        """Query root nodes of the improvement DAG."""
        return self._local_dag.get_roots()

    def query_frontier(self) -> list[DAGNode]:
        """Query the frontier (current best agents)."""
        return self._local_dag.get_frontier()

    @property
    def dag(self) -> ImprovementDAG:
        """Access the local DAG cache."""
        return self._local_dag
