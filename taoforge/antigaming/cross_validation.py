"""Validator cross-checking — detects outlier validators."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ValidatorTrust:
    """Trust score for a validator."""

    validator_uid: int
    trust_score: float = 1.0
    total_scores: int = 0
    deviation_sum: float = 0.0


class CrossValidator:
    """Compares validator scores against each other.

    Detects outlier validators who consistently deviate from consensus.
    Outliers get their trust score reduced.
    """

    def __init__(self, deviation_threshold: float = 0.2, decay_rate: float = 0.05) -> None:
        self.deviation_threshold = deviation_threshold
        self.decay_rate = decay_rate
        self._trust: dict[int, ValidatorTrust] = {}

    def record_scores(
        self,
        proposal_id: str,
        validator_scores: dict[int, float],
    ) -> dict[int, float]:
        """Record validator scores for a proposal and update trust.

        Args:
            proposal_id: The proposal being scored.
            validator_scores: Mapping of validator_uid -> score.

        Returns:
            Updated trust scores for each validator.
        """
        if not validator_scores:
            return {}

        # Compute consensus (median)
        scores = list(validator_scores.values())
        scores.sort()
        median = scores[len(scores) // 2]

        # Update trust for each validator
        updated = {}
        for uid, score in validator_scores.items():
            if uid not in self._trust:
                self._trust[uid] = ValidatorTrust(validator_uid=uid)

            record = self._trust[uid]
            deviation = abs(score - median)
            record.deviation_sum += deviation
            record.total_scores += 1

            if deviation > self.deviation_threshold:
                record.trust_score *= (1 - self.decay_rate)
            else:
                record.trust_score = min(1.0, record.trust_score + self.decay_rate * 0.5)

            updated[uid] = record.trust_score

        return updated

    def get_trust(self, validator_uid: int) -> float:
        """Get current trust score for a validator."""
        record = self._trust.get(validator_uid)
        return record.trust_score if record else 1.0

    def get_outliers(self, threshold: float = 0.5) -> list[int]:
        """Get validator UIDs with trust below threshold."""
        return [
            uid for uid, record in self._trust.items()
            if record.trust_score < threshold
        ]
