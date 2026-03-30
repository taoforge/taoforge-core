//! Hash gadgets for in-circuit hashing (Poseidon / SHA-256).
//!
//! Used for score commitments and weight hash verification inside ZK circuits.

use sha2::{Digest, Sha256};

/// Compute SHA-256 hash (out-of-circuit helper).
pub fn sha256_hash(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    let mut output = [0u8; 32];
    output.copy_from_slice(&result);
    output
}

/// Compute hash of a score value for commitment.
pub fn hash_score(score: f64) -> [u8; 32] {
    sha256_hash(&score.to_le_bytes())
}

// TODO: Implement Poseidon hash gadget for in-circuit use.
// Poseidon is more efficient than SHA-256 inside arithmetic circuits
// and is the standard choice for ZK-SNARK applications.
