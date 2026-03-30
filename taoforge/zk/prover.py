"""High-level ZK proof generation API for miners."""

from __future__ import annotations

import logging

from taoforge.utils.hashing import hash_score
from taoforge.zk.bridge import generate_proof
from taoforge.zk.types import ProofResult, ZKProof

logger = logging.getLogger(__name__)


class Prover:
    """High-level proof generation API.

    Miners use this to generate ZK proofs for their improvement proposals.
    Abstracts away circuit details and provides a clean interface.
    """

    def prove_baseline(
        self,
        weights_hash: str,
        eval_input_hashes: list[str],
        score: float,
        benchmark_id: str,
    ) -> ProofResult:
        """Generate a proof-of-baseline.

        Proves the agent achieved score S on benchmark B without revealing weights.
        """
        score_hash = hash_score(score)

        result = generate_proof(
            circuit_type="baseline",
            private_inputs={
                "weights_hash": weights_hash,
                "eval_input_hashes": eval_input_hashes,
                "score": score,
            },
            public_inputs={
                "benchmark_id": benchmark_id,
                "score_hash": score_hash,
            },
        )

        if result.success:
            logger.info(
                f"Baseline proof generated | benchmark={benchmark_id} | "
                f"time={result.generation_time_ms:.1f}ms"
            )

        return result

    def prove_improvement(
        self,
        base_weights_hash: str,
        delta_weights_hash: str,
        eval_input_hashes: list[str],
        base_score: float,
        delta_score: float,
        benchmark_id: str,
    ) -> ProofResult:
        """Generate a proof-of-improvement.

        Proves score_delta > score_base without revealing weights.
        """
        improvement = delta_score - base_score
        base_hash = hash_score(base_score)
        delta_hash = hash_score(delta_score)

        result = generate_proof(
            circuit_type="improvement",
            private_inputs={
                "base_weights_hash": base_weights_hash,
                "delta_weights_hash": delta_weights_hash,
                "eval_input_hashes": eval_input_hashes,
                "base_score": base_score,
                "delta_score": delta_score,
            },
            public_inputs={
                "benchmark_id": benchmark_id,
                "score_base_hash": base_hash,
                "score_delta_hash": delta_hash,
                "improvement_claim": improvement,
            },
        )

        if result.success:
            logger.info(
                f"Improvement proof generated | delta={improvement:.4f} | "
                f"time={result.generation_time_ms:.1f}ms"
            )

        return result

    def prove_lineage(
        self,
        parent_hash: str,
        current_hash: str,
        mutation_delta_hash: str,
    ) -> ProofResult:
        """Generate a proof-of-lineage.

        Proves the current agent derives from the claimed parent via mutation.
        """
        return generate_proof(
            circuit_type="lineage",
            private_inputs={
                "parent_hash": parent_hash,
                "mutation_delta_hash": mutation_delta_hash,
            },
            public_inputs={
                "parent_hash": parent_hash,
                "current_hash": current_hash,
            },
        )
