"""Configuration for TaoForge neurons — Pydantic BaseSettings with env/CLI support."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class NodeConfig(BaseSettings):
    """Base configuration shared by all TaoForge nodes."""

    model_config = {"env_prefix": "TAOFORGE_"}

    # Node identity
    node_name: str = "taoforge_node"
    key_file: str = "~/.taoforge/node.key"

    # Networking
    host: str = "0.0.0.0"
    port: int = 8091
    seed_peers: list[str] = Field(default_factory=list)

    # Logging
    log_level: str = "INFO"
    device: str = "cuda"


class MinerConfig(NodeConfig):
    """Miner-specific configuration."""

    node_name: str = "taoforge_miner"
    port: int = 8091

    # Proposal settings
    min_bond: float = 1.0
    max_compound_parts: int = 4


class ValidatorConfig(NodeConfig):
    """Validator-specific configuration."""

    node_name: str = "taoforge_validator"
    port: int = 8092

    # Validation loop
    epoch_length: int = 100
    query_interval: float = 12.0

    # Scoring weights
    w_improvement: float = 0.35
    w_novelty: float = 0.25
    w_breadth: float = 0.20
    w_regression: float = 0.15
    w_gaming: float = 0.05

    # Evaluation
    holdout_fraction: float = 0.2
    min_agreement: float = 0.67
