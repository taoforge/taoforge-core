"""Subnet registry — catalog of known Bittensor subnets and their eval criteria."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SubnetDomain(Enum):
    """High-level domain categories for subnets."""

    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    CODE = "code"
    DATA = "data"
    AUDIO = "audio"
    VIDEO = "video"
    STORAGE = "storage"
    INFERENCE = "inference"
    SEARCH = "search"
    OTHER = "other"


@dataclass
class SubnetProfile:
    """Profile of a Bittensor subnet — what it does and how it evaluates miners.

    This is the agent's understanding of a target subnet. It includes
    the evaluation criteria, scoring rubric, and known competitive dynamics.
    """

    netuid: int
    name: str
    domain: SubnetDomain
    description: str = ""

    # Evaluation criteria
    eval_criteria: list[str] = field(default_factory=list)
    scoring_rubric: dict[str, float] = field(default_factory=dict)
    benchmark_type: str = ""  # e.g., "text_quality", "latency", "accuracy"

    # Competitive dynamics
    num_miners: int = 0
    avg_incentive: float = 0.0
    difficulty_estimate: float = 0.5  # 0 = easy, 1 = extremely competitive

    # Agent interaction mode
    mode: str = "observer"  # "competitor" | "observer" | "offline"

    # Technical requirements
    min_gpu_vram_gb: int = 0
    model_type: str = ""  # e.g., "llm", "diffusion", "classifier"
    api_endpoint: str = ""  # If subnet has a standard API

    # Metadata
    source_repo: str = ""
    docs_url: str = ""
    last_updated: float = 0.0


class SubnetRegistry:
    """Catalog of known subnets with their profiles.

    Agents use this to discover and select target subnets for improvement.
    """

    def __init__(self) -> None:
        self._subnets: dict[int, SubnetProfile] = {}
        self._load_defaults()

    def register(self, profile: SubnetProfile) -> None:
        """Register or update a subnet profile."""
        self._subnets[profile.netuid] = profile
        logger.info(f"Subnet registered: netuid={profile.netuid} name={profile.name}")

    def get(self, netuid: int) -> Optional[SubnetProfile]:
        return self._subnets.get(netuid)

    def get_by_domain(self, domain: SubnetDomain) -> list[SubnetProfile]:
        return [s for s in self._subnets.values() if s.domain == domain]

    def get_all(self) -> list[SubnetProfile]:
        return list(self._subnets.values())

    def get_easiest(self, top_n: int = 5) -> list[SubnetProfile]:
        """Get subnets ranked by lowest difficulty (easiest to improve on)."""
        return sorted(self._subnets.values(), key=lambda s: s.difficulty_estimate)[:top_n]

    def get_most_rewarding(self, top_n: int = 5) -> list[SubnetProfile]:
        """Get subnets ranked by highest average incentive."""
        return sorted(self._subnets.values(), key=lambda s: s.avg_incentive, reverse=True)[:top_n]

    def _load_defaults(self) -> None:
        """Load default subnet profiles for well-known Bittensor subnets."""
        defaults = [
            SubnetProfile(
                netuid=0,
                name="Subnet Analysis",
                domain=SubnetDomain.DATA,
                description="Self-evaluating subnet metagraph analysis",
                eval_criteria=["specificity", "accuracy", "depth", "self_consistency", "criteria_following"],
                benchmark_type="subnet_analysis",
                model_type="llm",
            ),
            SubnetProfile(
                netuid=1,
                name="Text Prompting",
                domain=SubnetDomain.TEXT_GENERATION,
                description="Text generation and prompting subnet",
                eval_criteria=["coherence", "relevance", "creativity"],
                benchmark_type="text_quality",
                model_type="llm",
            ),
            SubnetProfile(
                netuid=5,
                name="Image Generation",
                domain=SubnetDomain.IMAGE_GENERATION,
                description="Text-to-image generation",
                eval_criteria=["fidelity", "prompt_adherence", "aesthetic_score"],
                benchmark_type="image_quality",
                model_type="diffusion",
            ),
            SubnetProfile(
                netuid=27,
                name="Compute",
                domain=SubnetDomain.INFERENCE,
                description="Decentralized compute and inference",
                eval_criteria=["latency", "throughput", "reliability"],
                benchmark_type="performance",
                model_type="inference",
            ),
        ]
        for profile in defaults:
            self._subnets[profile.netuid] = profile
