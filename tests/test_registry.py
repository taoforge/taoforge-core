"""Tests for the registry DAG and reputation system."""

import time

from taoforge.registry.dag import ImprovementDAG
from taoforge.registry.node import DAGNode
from taoforge.registry.reputation import ReputationSystem


def test_dag_add_and_get():
    dag = ImprovementDAG()
    node = DAGNode(node_id="n1", agent_id="a1", mutation_type="lora_merge")
    dag.add_node(node)
    assert dag.get_node("n1") is node
    assert dag.size == 1


def test_dag_lineage():
    dag = ImprovementDAG()
    root = DAGNode(node_id="n1", agent_id="a1", timestamp=1.0)
    child = DAGNode(node_id="n2", agent_id="a1", parent_id="n1", timestamp=2.0)
    grandchild = DAGNode(node_id="n3", agent_id="a1", parent_id="n2", timestamp=3.0)
    dag.add_node(root)
    dag.add_node(child)
    dag.add_node(grandchild)

    lineage = dag.get_lineage("n3")
    assert len(lineage) == 3
    assert lineage[0].node_id == "n3"
    assert lineage[2].node_id == "n1"


def test_dag_frontier():
    dag = ImprovementDAG()
    dag.add_node(DAGNode(node_id="n1", agent_id="a1"))
    dag.add_node(DAGNode(node_id="n2", agent_id="a1", parent_id="n1"))
    frontier = dag.get_frontier()
    assert len(frontier) == 1
    assert frontier[0].node_id == "n2"


def test_dag_agent_history():
    dag = ImprovementDAG()
    dag.add_node(DAGNode(node_id="n1", agent_id="a1", timestamp=1.0))
    dag.add_node(DAGNode(node_id="n2", agent_id="a1", timestamp=2.0))
    dag.add_node(DAGNode(node_id="n3", agent_id="a2", timestamp=3.0))
    history = dag.get_agent_history("a1")
    assert len(history) == 2


def test_reputation_update():
    rep = ReputationSystem(decay_rate=0.0)  # No decay for testing
    rep.update("a1", 0.1)
    assert rep.get_reputation("a1") > 0


def test_reputation_streak():
    rep = ReputationSystem(decay_rate=0.0, streak_multiplier=0.1)
    rep.update("a1", 0.1)
    rep.update("a1", 0.1)
    rep.update("a1", 0.1)
    record = rep.get_record("a1")
    assert record.current_streak == 3
    assert record.total_improvements == 3


def test_reputation_break_streak():
    rep = ReputationSystem(decay_rate=0.0)
    rep.update("a1", 0.1)
    rep.update("a1", 0.1)
    rep.break_streak("a1")
    record = rep.get_record("a1")
    assert record.current_streak == 0


def test_reputation_leaderboard():
    rep = ReputationSystem(decay_rate=0.0)
    rep.update("a1", 0.5)
    rep.update("a2", 0.8)
    rep.update("a3", 0.3)
    board = rep.get_leaderboard(top_n=2)
    assert len(board) == 2
    assert board[0].agent_id == "a2"
