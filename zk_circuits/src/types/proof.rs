//! Proof types — Proof, VerificationKey, ProvingKey.

use serde::{Deserialize, Serialize};

/// The type of ZK circuit.
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum CircuitType {
    Baseline,
    Improvement,
    Lineage,
    NonRegression,
}

impl CircuitType {
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "baseline" => Some(Self::Baseline),
            "improvement" => Some(Self::Improvement),
            "lineage" => Some(Self::Lineage),
            "non_regression" => Some(Self::NonRegression),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            Self::Baseline => "baseline",
            Self::Improvement => "improvement",
            Self::Lineage => "lineage",
            Self::NonRegression => "non_regression",
        }
    }
}

/// A generated ZK proof.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Proof {
    pub bytes: Vec<u8>,
    pub circuit_type: CircuitType,
}

/// Verification key for a circuit.
#[derive(Clone, Debug)]
pub struct VerificationKey {
    pub bytes: Vec<u8>,
    pub circuit_type: CircuitType,
}

/// Proving key for a circuit.
#[derive(Clone, Debug)]
pub struct ProvingKey {
    pub bytes: Vec<u8>,
    pub circuit_type: CircuitType,
}
