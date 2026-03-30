//! Input types for ZK circuits.

use serde::{Deserialize, Serialize};

/// Public inputs visible to validators.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PublicInput {
    pub benchmark_id: String,
    pub score_base_hash: [u8; 32],
    pub score_delta_hash: [u8; 32],
    pub improvement_claim: f64,
}

/// Private inputs known only to the agent.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PrivateInput {
    /// Commitment to base model weights
    pub weights_base_hash: [u8; 32],
    /// Commitment to mutated model weights
    pub weights_delta_hash: [u8; 32],
    /// Eval input hashes (for reproducibility)
    pub eval_input_hashes: Vec<[u8; 32]>,
    /// Actual scores (committed via hashes in public inputs)
    pub score_base: f64,
    pub score_delta: f64,
}
