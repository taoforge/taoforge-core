"""Gaming detection orchestrator — combines all anti-gaming checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from taoforge.evaluation.results import EvalResult
from taoforge.proposal.schema import ImprovementProposal


@dataclass
class GamingReport:
    """Results of anti-gaming analysis."""

    is_suspicious: bool = False
    combined_score: float = 0.0
    checks: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


class GamingDetector:
    """Orchestrates all anti-gaming checks for a proposal.

    Combines benchmark rotation enforcement, holdout discrepancy detection,
    cross-validation results, and historical pattern analysis.
    """

    def __init__(self, suspicion_threshold: float = 0.5) -> None:
        self.suspicion_threshold = suspicion_threshold

    def detect(
        self,
        proposal: ImprovementProposal,
        public_result: EvalResult,
        holdout_result: EvalResult | None = None,
        history: list[ImprovementProposal] | None = None,
    ) -> GamingReport:
        """Run all anti-gaming checks and produce a report.

        Args:
            proposal: The proposal to check.
            public_result: Public benchmark evaluation result.
            holdout_result: Private holdout evaluation result.
            history: Recent proposals from the same agent.

        Returns:
            GamingReport with combined score and per-check details.
        """
        report = GamingReport()

        # Check 1: Public vs holdout discrepancy
        if holdout_result is not None:
            discrepancy = public_result.aggregate_score - holdout_result.aggregate_score
            report.checks["holdout_discrepancy"] = max(discrepancy, 0.0)
            if discrepancy > 0.1:
                report.reasons.append(
                    f"Public score exceeds holdout by {discrepancy:.3f}"
                )

        # Check 2: Suspiciously small repeated claims
        if history:
            agent_history = [p for p in history if p.agent_id == proposal.agent_id]
            if len(agent_history) > 5:
                claims = [p.improvement_claim for p in agent_history[-5:]]
                avg = sum(claims) / len(claims)
                if avg < 0.005:
                    report.checks["micro_grinding"] = 0.3
                    report.reasons.append("Pattern of very small improvement claims")

        # Check 3: Benchmark version mismatch
        # TODO: Verify proposal references the currently active benchmark

        # Combine scores
        if report.checks:
            report.combined_score = sum(report.checks.values()) / len(report.checks)
        report.is_suspicious = report.combined_score > self.suspicion_threshold

        return report
