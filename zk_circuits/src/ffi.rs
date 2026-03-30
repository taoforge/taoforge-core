//! PyO3 FFI bridge — exposes proof generation and verification to Python.

use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Generate a ZK proof for the specified circuit type.
///
/// # Arguments
/// * `circuit_type` - One of: "baseline", "improvement", "lineage", "non_regression"
/// * `private_inputs_json` - JSON-encoded private inputs
/// * `public_inputs_json` - JSON-encoded public inputs
///
/// # Returns
/// Proof bytes as a Python bytes object.
#[pyfunction]
pub fn generate_proof(
    circuit_type: &str,
    private_inputs_json: &str,
    public_inputs_json: &str,
) -> PyResult<Vec<u8>> {
    let _private: serde_json::Value = serde_json::from_str(private_inputs_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid private inputs: {}", e)))?;
    let _public: serde_json::Value = serde_json::from_str(public_inputs_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid public inputs: {}", e)))?;

    match circuit_type {
        "baseline" => {
            // TODO: Generate ProofOfBaseline
            Ok(vec![0u8; 64]) // Placeholder proof bytes
        }
        "improvement" => {
            // TODO: Generate ProofOfImprovement
            Ok(vec![0u8; 128]) // Placeholder proof bytes
        }
        "lineage" => {
            // TODO: Generate ProofOfLineage
            Ok(vec![0u8; 96]) // Placeholder proof bytes
        }
        "non_regression" => {
            // TODO: Generate ProofOfNonRegression
            Ok(vec![0u8; 96]) // Placeholder proof bytes
        }
        _ => Err(pyo3::exceptions::PyValueError::new_err(
            format!("Unknown circuit type: {}", circuit_type),
        )),
    }
}

/// Verify a ZK proof for the specified circuit type.
///
/// # Arguments
/// * `circuit_type` - The circuit type that produced this proof
/// * `proof_bytes` - The proof to verify
/// * `public_inputs_json` - JSON-encoded public inputs
///
/// # Returns
/// Boolean indicating whether the proof is valid.
#[pyfunction]
pub fn verify_proof(
    circuit_type: &str,
    proof_bytes: &[u8],
    public_inputs_json: &str,
) -> PyResult<bool> {
    let _public: serde_json::Value = serde_json::from_str(public_inputs_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid public inputs: {}", e)))?;

    match circuit_type {
        "baseline" | "improvement" | "lineage" | "non_regression" => {
            // TODO: Implement actual proof verification
            // For now, accept any non-empty proof
            Ok(!proof_bytes.is_empty())
        }
        _ => Err(pyo3::exceptions::PyValueError::new_err(
            format!("Unknown circuit type: {}", circuit_type),
        )),
    }
}

/// Get information about a circuit type.
#[pyfunction]
pub fn get_circuit_info(circuit_type: &str) -> PyResult<String> {
    let info = match circuit_type {
        "baseline" => serde_json::json!({
            "name": "ProofOfBaseline",
            "description": "Prove baseline eval score without revealing weights",
            "public_inputs": ["benchmark_id", "score_hash"],
            "status": "stub"
        }),
        "improvement" => serde_json::json!({
            "name": "ProofOfImprovement",
            "description": "Prove score improved after mutation",
            "public_inputs": ["benchmark_id", "score_base_hash", "score_delta_hash", "improvement_claim"],
            "status": "stub"
        }),
        "lineage" => serde_json::json!({
            "name": "ProofOfLineage",
            "description": "Prove agent derives from claimed parent",
            "public_inputs": ["parent_hash", "current_hash"],
            "status": "stub"
        }),
        "non_regression" => serde_json::json!({
            "name": "ProofOfNonRegression",
            "description": "Prove auxiliary scores didn't regress",
            "public_inputs": ["benchmark_id", "threshold", "score_hashes"],
            "status": "stub"
        }),
        _ => return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Unknown circuit type: {}", circuit_type),
        )),
    };

    Ok(info.to_string())
}
