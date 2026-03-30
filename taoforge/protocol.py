"""TaoForge wire protocol — message types for validator-miner communication."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ImprovementProposalMessage(BaseModel):
    """Primary message: miner submits an improvement proposal to validators.

    Validators send this as a challenge; miners populate the response fields
    with their proposal data, ZK proofs, and bonded stake.
    """

    # --- Request fields (validator → miner) ---
    challenge_id: str = ""
    benchmark_id: str = ""

    # --- Response fields (miner → validator) ---
    proposal_id: Optional[str] = None
    agent_hotkey: Optional[str] = None
    mutation_type: Optional[str] = None
    parent_delta_hash: Optional[str] = None

    # ZK proof data
    baseline_proof_bytes: Optional[bytes] = None
    baseline_score_hash: Optional[str] = None
    delta_proof_bytes: Optional[bytes] = None
    delta_score_hash: Optional[str] = None
    improvement_claim: Optional[float] = None

    # Bond
    bond_amount: Optional[float] = None

    # Metadata
    mutation_description: Optional[str] = None
    novelty_claim: Optional[str] = None


class BenchmarkChallengeMessage(BaseModel):
    """Validator sends a benchmark challenge to re-evaluate a miner's agent.

    Used during validation to independently verify agent performance.
    """

    # --- Request fields ---
    challenge_id: str = ""
    task_ids: list[str] = Field(default_factory=list)
    benchmark_version: str = ""

    # --- Response fields ---
    task_scores: Optional[dict[str, float]] = None
    aggregate_score: Optional[float] = None
    execution_time_ms: Optional[float] = None


class ProofVerificationMessage(BaseModel):
    """Carries ZK proof bytes for cross-validator verification.

    Validators can request other validators to verify a proof they received.
    """

    # --- Request fields ---
    proof_bytes: bytes = b""
    public_inputs_json: str = ""
    circuit_type: str = ""  # "baseline" | "improvement" | "lineage" | "non_regression"

    # --- Response fields ---
    is_valid: Optional[bool] = None
    verification_time_ms: Optional[float] = None
