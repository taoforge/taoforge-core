//! Benchmarks for proof generation and verification.

use criterion::{criterion_group, criterion_main, Criterion};
use taoforge_zk::prover::engine::generate;
use taoforge_zk::types::proof::CircuitType;
use taoforge_zk::verifier::engine::verify;

fn bench_proof_generation(c: &mut Criterion) {
    c.bench_function("generate_improvement_proof", |b| {
        b.iter(|| {
            generate(CircuitType::Improvement, b"private", b"public").unwrap();
        })
    });
}

fn bench_proof_verification(c: &mut Criterion) {
    let proof = generate(CircuitType::Improvement, b"private", b"public").unwrap();

    c.bench_function("verify_improvement_proof", |b| {
        b.iter(|| {
            verify(&proof, b"public").unwrap();
        })
    });
}

criterion_group!(benches, bench_proof_generation, bench_proof_verification);
criterion_main!(benches);
