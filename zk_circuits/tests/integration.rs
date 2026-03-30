//! Integration tests for TaoForge ZK circuits.

use taoforge_zk::prover::engine::generate;
use taoforge_zk::types::proof::CircuitType;
use taoforge_zk::verifier::engine::verify;

#[test]
fn test_improvement_proof_roundtrip() {
    let proof = generate(
        CircuitType::Improvement,
        b"private_inputs",
        b"public_inputs",
    )
    .expect("Proof generation should succeed");

    assert_eq!(proof.circuit_type, CircuitType::Improvement);
    assert!(!proof.bytes.is_empty());

    let valid = verify(&proof, b"public_inputs").expect("Verification should not error");
    assert!(valid, "Stub proof should verify");
}

#[test]
fn test_baseline_proof_roundtrip() {
    let proof = generate(CircuitType::Baseline, b"private", b"public")
        .expect("Baseline proof generation should succeed");

    assert_eq!(proof.circuit_type, CircuitType::Baseline);
    let valid = verify(&proof, b"public").expect("Verification should not error");
    assert!(valid);
}

#[test]
fn test_lineage_proof_roundtrip() {
    let proof = generate(CircuitType::Lineage, b"private", b"public")
        .expect("Lineage proof generation should succeed");

    assert_eq!(proof.circuit_type, CircuitType::Lineage);
    let valid = verify(&proof, b"public").expect("Verification should not error");
    assert!(valid);
}

#[test]
fn test_empty_proof_fails_verification() {
    use taoforge_zk::types::proof::Proof;

    let empty_proof = Proof {
        bytes: vec![],
        circuit_type: CircuitType::Improvement,
    };

    let valid = verify(&empty_proof, b"public").expect("Verification should not error");
    assert!(!valid, "Empty proof should not verify");
}
