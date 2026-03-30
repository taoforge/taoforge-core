"""Environment ABC — domain-agnostic interface for open-ended agent evaluation.

Any environment (subnet, codebase, medical records, market data, ...) implements
this interface. Agents receive raw context and explore freely — no prescribed
objectives. Scored only on whether claims are factually grounded in the data.

This is the Level 2 autonomy model: we define the domain, agents discover the tasks.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class EnvironmentContext:
    """Raw environment data passed to the agent.

    Attributes:
        domain:         Human-readable domain name (e.g. "bittensor_subnet_1").
        raw_data:       Formatted text summary — what the agent reads.
        structured_data: Machine-readable dict — used by the grounding verifier.
        metadata:       Arbitrary additional context (block, timestamp, etc.).
    """

    domain: str
    raw_data: str
    structured_data: dict
    metadata: dict = field(default_factory=dict)


@dataclass
class GroundingResult:
    """Result of verifying that agent output is factually grounded.

    Grounding verification answers: "Are the claims in this output
    supported by the environment data?" It does NOT ask whether the
    agent covered the right topics or reached the right conclusions.

    Attributes:
        score:           Composite grounding score in [0, 1].
        verified_claims: Number of claims that checked out.
        total_claims:    Total claims attempted to verify.
        details:         Per-scorer breakdown (specificity, accuracy, depth, ...).
    """

    score: float
    verified_claims: int
    total_claims: int
    details: dict = field(default_factory=dict)


@dataclass
class CycleState:
    """Shared mutable state across phases in one eval cycle.

    Phase 1 (analysis) writes prior_output + prior_grounding + prior_score.
    Phase 2 (self-eval) writes self_eval_rating + self_eval_criteria.
    Phase 3 (evolution) reads criteria and re-analyzes.
    """

    prior_output: str = ""
    prior_grounding: GroundingResult | None = None
    prior_score: float = 0.0
    self_eval_rating: float = 0.0
    self_eval_criteria: list[str] = field(default_factory=list)
    cycle_number: int = 0


class Environment(abc.ABC):
    """Abstract base class for open-ended evaluation environments.

    Subclass this to plug any domain into the TaoForge harness.
    The implementing class owns:
      - How to fetch/provide environment data
      - How to format it for agent consumption
      - How to verify factual grounding of agent output

    It does NOT define what the agent should work on. That is the agent's job.
    """

    @property
    @abc.abstractmethod
    def domain(self) -> str:
        """Human-readable domain identifier (e.g. 'bittensor_subnet_1')."""
        ...

    @abc.abstractmethod
    def get_context(self) -> EnvironmentContext:
        """Return the current environment snapshot for agent consumption.

        Called once per eval cycle. Implementations may refresh live data
        or return a cached snapshot.
        """
        ...

    @abc.abstractmethod
    def verify_grounding(self, output: str) -> GroundingResult:
        """Check whether agent output is factually grounded in this environment.

        Does NOT assess whether the agent worked on the right problem.
        Only checks: are the specific claims made in `output` accurate?

        Args:
            output: Raw text output from the agent.

        Returns:
            GroundingResult with a score in [0, 1] and detailed breakdown.
        """
        ...
