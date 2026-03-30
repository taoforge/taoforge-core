//! TaoForge ZK Circuits — proof-of-improvement infrastructure.
//!
//! Provides zero-knowledge proof circuits for the TaoForge subnet:
//! - ProofOfBaseline: Prove baseline eval score without revealing weights
//! - ProofOfImprovement: Prove score improved after mutation
//! - ProofOfLineage: Prove agent derives from claimed parent
//! - ProofOfNonRegression: Prove auxiliary scores didn't regress

pub mod circuits;
pub mod ffi;
pub mod prover;
pub mod types;
pub mod utils;
pub mod verifier;

use pyo3::prelude::*;

/// Python module for TaoForge ZK circuits.
#[pymodule]
fn taoforge_zk(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ffi::generate_proof, m)?)?;
    m.add_function(wrap_pyfunction!(ffi::verify_proof, m)?)?;
    m.add_function(wrap_pyfunction!(ffi::get_circuit_info, m)?)?;
    Ok(())
}
