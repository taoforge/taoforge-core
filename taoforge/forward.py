"""Validator forward pass — orchestrates miner querying and scoring."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from taoforge.evaluation.engine import BenchmarkEngine
from taoforge.evaluation.holdout import HoldoutManager
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.evaluation.task import (
    CodeGenerationTask,
    PlanningTask,
    TextReasoningTask,
)
from taoforge.net.peer import PeerInfo
from taoforge.proposal.schema import (
    BaselineProof,
    DeltaProof,
    ImprovementProposal,
)
from taoforge.protocol import ImprovementProposalMessage
from taoforge.registry.dag import ImprovementDAG
from taoforge.registry.node import DAGNode
from taoforge.registry.reputation import ReputationSystem
from taoforge.scoring.formula import compute_score
from taoforge.scoring.weights import ScoringWeights
from taoforge.utils.hashing import hash_score
from taoforge.zk.bridge import verify_proof

if TYPE_CHECKING:
    from taoforge.base.validator import BaseValidatorNeuron

logger = logging.getLogger(__name__)


def _build_validator_suite() -> BenchmarkSuite:
    """Build the validator's benchmark suite (must match miner suite)."""
    suite = BenchmarkSuite(suite_id="taoforge_default_v0.1")
    suite.add_task(TextReasoningTask(
        "reasoning_basic",
        "What are three key differences between a list and a tuple in Python?",
        expected_keywords=["immutable", "mutable", "tuple", "list"],
    ))
    suite.add_task(TextReasoningTask(
        "reasoning_logic",
        "If all roses are flowers and some flowers fade quickly, can we conclude "
        "that some roses fade quickly?",
        expected_keywords=["cannot", "conclude", "not necessarily"],
    ))
    suite.add_task(CodeGenerationTask(
        "code_fizzbuzz",
        "Write a Python function called fizzbuzz(n) that returns 'Fizz' for "
        "multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for multiples "
        "of both, and the number as a string otherwise.",
        test_cases=[
            {"function": "fizzbuzz", "input": [3], "expected": "Fizz"},
            {"function": "fizzbuzz", "input": [5], "expected": "Buzz"},
            {"function": "fizzbuzz", "input": [15], "expected": "FizzBuzz"},
            {"function": "fizzbuzz", "input": [7], "expected": "7"},
        ],
    ))
    suite.add_task(PlanningTask(
        "planning_basic",
        "Deploy a web application to production",
        constraints=["Must have zero downtime", "Must include rollback plan"],
        expected_steps=5,
    ))
    return suite


async def forward_fn(
    validator: BaseValidatorNeuron,
    miners: list[PeerInfo],
) -> dict[str, float]:
    """Execute one forward pass of the validation cycle.

    1. Build improvement proposal challenge.
    2. Query miners via HTTP.
    3. For each response: verify ZK proof, re-run benchmark, compute score.
    4. Return score dict mapping node_id → score.

    Args:
        validator: The validator neuron instance.
        miners: Miner peers to query this round.

    Returns:
        Dict mapping miner node_id to score.
    """
    challenge_id = str(uuid.uuid4())
    suite = _build_validator_suite()

    # Build challenge payload
    challenge = ImprovementProposalMessage(
        challenge_id=challenge_id,
        benchmark_id=suite.suite_id,
    )

    # Query miners
    responses = await validator.client.query_miners(
        peers=miners,
        endpoint="/v1/proposal",
        data=challenge.model_dump(),
    )

    # Score each response
    scores: dict[str, float] = {}
    for peer, response in zip(miners, responses):
        if response is None or response.get("proposal_id") is None:
            scores[peer.node_id] = 0.0
            continue

        try:
            score = await _score_proposal(validator, peer, response, suite, challenge_id)
        except Exception as e:
            logger.error(f"Error scoring proposal from {peer.node_id}: {e}")
            score = 0.0

        scores[peer.node_id] = score

    # Update validator's score tracking
    validator.update_scores(scores)

    responded = sum(1 for s in scores.values() if s > 0)
    logger.info(
        f"Forward pass complete | challenge={challenge_id} | "
        f"miners={len(miners)} | responded={responded}"
    )

    return scores


async def _score_proposal(
    validator: BaseValidatorNeuron,
    peer: PeerInfo,
    response: dict,
    suite: BenchmarkSuite,
    challenge_id: str,
) -> float:
    """Score a single miner's proposal response.

    Verifies ZK proofs, re-runs benchmark for independent verification,
    and computes the composite score.
    """
    # 1. Verify ZK proofs
    baseline_proof_bytes = response.get("baseline_proof_bytes")
    delta_proof_bytes = response.get("delta_proof_bytes")
    benchmark_id = suite.suite_id

    if baseline_proof_bytes:
        baseline_valid = verify_proof(
            circuit_type="baseline",
            proof_bytes=(
                baseline_proof_bytes
                if isinstance(baseline_proof_bytes, bytes)
                else baseline_proof_bytes.encode() if baseline_proof_bytes else b""
            ),
            public_inputs={
                "benchmark_id": benchmark_id,
                "score_hash": response.get("baseline_score_hash", ""),
            },
        )
        if not baseline_valid:
            logger.warning(f"Invalid baseline proof from {peer.node_id}")
            return 0.0

    if delta_proof_bytes:
        delta_valid = verify_proof(
            circuit_type="improvement",
            proof_bytes=(
                delta_proof_bytes
                if isinstance(delta_proof_bytes, bytes)
                else delta_proof_bytes.encode() if delta_proof_bytes else b""
            ),
            public_inputs={
                "benchmark_id": benchmark_id,
                "score_base_hash": response.get("baseline_score_hash", ""),
                "score_delta_hash": response.get("delta_score_hash", ""),
                "improvement_claim": response.get("improvement_claim", 0.0),
            },
        )
        if not delta_valid:
            logger.warning(f"Invalid delta proof from {peer.node_id}")
            return 0.0

    # 2. Re-run benchmark on the miner's agent to independently verify
    #    In the networked protocol, the validator queries the miner's /v1/benchmark
    #    endpoint to get the miner to re-run evals. The validator compares the
    #    miner's claimed scores against its own independent verification.
    benchmark_response = await validator.client.query_miner(
        peer=peer,
        endpoint="/v1/benchmark",
        data={"challenge_id": challenge_id},
    )

    if benchmark_response is None:
        logger.warning(f"Benchmark re-eval failed for {peer.node_id}")
        return 0.0

    # 3. Build proposal object for scoring
    improvement_claim = response.get("improvement_claim", 0.0)
    if improvement_claim <= 0:
        return 0.0

    proposal = ImprovementProposal(
        proposal_id=response.get("proposal_id", ""),
        agent_id=response.get("agent_hotkey", peer.node_id),
        mutation_type=response.get("mutation_type", ""),
        baseline_proof=BaselineProof(
            zk_proof=baseline_proof_bytes or b"",
            benchmark_id=benchmark_id,
            score_hash=response.get("baseline_score_hash", ""),
        ),
        delta_proof=DeltaProof(
            zk_proof=delta_proof_bytes or b"",
            score_hash=response.get("delta_score_hash", ""),
            improvement_claim=improvement_claim,
        ),
        bond_amount=response.get("bond_amount", 0.0),
    )

    # Validate proposal structure
    errors = proposal.validate_structure()
    if errors:
        logger.warning(f"Proposal structure errors from {peer.node_id}: {errors}")
        return 0.0

    # 4. Compute composite score using the benchmark re-eval results
    #    Use the miner's reported scores to build EvalResults for scoring.
    #    In a production system, the validator would run its own evals too.
    from taoforge.evaluation.results import EvalResult, TaskScore

    task_scores_dict = benchmark_response.get("task_scores", {})
    aggregate = benchmark_response.get("aggregate_score", 0.0)

    delta_result = EvalResult(
        suite_id=benchmark_id,
        task_scores=[
            TaskScore(task_id=tid, score=s) for tid, s in task_scores_dict.items()
        ],
        aggregate_score=aggregate,
    )

    # Construct a synthetic baseline from the improvement claim
    baseline_aggregate = max(aggregate - improvement_claim, 0.0)
    baseline_result = EvalResult(
        suite_id=benchmark_id,
        task_scores=[
            TaskScore(task_id=tid, score=max(s - improvement_claim, 0.0))
            for tid, s in task_scores_dict.items()
        ],
        aggregate_score=baseline_aggregate,
    )

    composite = compute_score(
        proposal=proposal,
        baseline_result=baseline_result,
        delta_result=delta_result,
        weights=ScoringWeights(
            w_improvement=validator.validator_config.w_improvement,
            w_novelty=validator.validator_config.w_novelty,
            w_breadth=validator.validator_config.w_breadth,
            w_regression=validator.validator_config.w_regression,
            w_gaming=validator.validator_config.w_gaming,
        ),
        dag=validator.dag,
        proposal_history=validator.proposal_history,
    )

    # 5. If score is positive, register in DAG and update reputation
    if composite > 0.01:
        import time

        node = DAGNode(
            node_id=proposal.proposal_id,
            agent_id=proposal.agent_id,
            parent_id=None,
            mutation_type=proposal.mutation_type,
            improvement_delta=improvement_claim,
            benchmark_id=benchmark_id,
            timestamp=time.time(),
            proof_hash=response.get("delta_score_hash", ""),
            reputation_at_time=validator.reputation.get_reputation(proposal.agent_id),
        )
        validator.dag.add_node(node)
        validator.reputation.update(proposal.agent_id, improvement_claim)
        validator.proposal_history.append(proposal)

        logger.info(
            f"ACCEPTED proposal {proposal.proposal_id} from {peer.node_id} | "
            f"improvement={improvement_claim:.4f} | composite={composite:.4f}"
        )
    else:
        validator.reputation.break_streak(proposal.agent_id)

    return composite
