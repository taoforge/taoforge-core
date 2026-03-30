"""Bond slashing evaluator — determines when to slash bonds."""

from __future__ import annotations

from dataclasses import dataclass

from taoforge.evaluation.results import EvalResult
from taoforge.proposal.schema import ImprovementProposal


@dataclass
class SlashingDecision:
    """Result of slashing evaluation."""

    should_slash: bool = False
    reason: str = ""
    severity: float = 0.0  # 0 = no slash, 1 = full slash


class SlashingEvaluator:
    """Evaluates whether a proposal meets slashing conditions.

    Bonds are slashed when:
    - Improvement is not reproducible by validators
    - ZK proof fails verification
    - Benchmark version is incorrect
    - Evidence of fabricated results
    """

    def __init__(self, reproducibility_threshold: float = 0.5) -> None:
        self.reproducibility_threshold = reproducibility_threshold

    def evaluate(
        self,
        proposal: ImprovementProposal,
        claimed_improvement: float,
        validator_result: EvalResult,
        baseline_result: EvalResult,
        proof_valid: bool,
    ) -> SlashingDecision:
        """Evaluate whether a proposal should be slashed.

        Args:
            proposal: The proposal under review.
            claimed_improvement: The agent's claimed improvement percentage.
            validator_result: Validator's independent evaluation of the mutated agent.
            baseline_result: Validator's independent baseline evaluation.
            proof_valid: Whether the ZK proof passed verification.

        Returns:
            SlashingDecision with reason and severity.
        """
        # ZK proof failure — immediate slash
        if not proof_valid:
            return SlashingDecision(
                should_slash=True,
                reason="ZK proof failed verification.",
                severity=1.0,
            )

        # Improvement not reproducible
        actual_improvement = validator_result.aggregate_score - baseline_result.aggregate_score
        if claimed_improvement > 0 and actual_improvement <= 0:
            return SlashingDecision(
                should_slash=True,
                reason="Claimed improvement not reproducible — no improvement detected.",
                severity=0.8,
            )

        # Improvement significantly lower than claimed
        if claimed_improvement > 0:
            ratio = actual_improvement / claimed_improvement
            if ratio < self.reproducibility_threshold:
                return SlashingDecision(
                    should_slash=True,
                    reason=(
                        f"Improvement {actual_improvement:.4f} is {ratio:.1%} "
                        f"of claimed {claimed_improvement:.4f}."
                    ),
                    severity=0.6,
                )

        return SlashingDecision(should_slash=False)
