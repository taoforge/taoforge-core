//! ProofOfLineage circuit — proves the current agent derives from the claimed parent.
//!
//! Constraint: hash(parent_weights + mutation_delta) == current_weights_hash

use halo2_proofs::circuit::{Layouter, SimpleFloorPlanner, Value};
use halo2_proofs::plonk::{Circuit, ConstraintSystem, Error};
use ff::PrimeField;

#[derive(Clone, Debug)]
pub struct LineageConfig {
    // TODO: Define columns
}

#[derive(Clone, Debug, Default)]
pub struct ProofOfLineageCircuit<F: PrimeField> {
    /// Parent weights hash (private)
    pub parent_hash: Value<F>,
    /// Mutation delta hash (private)
    pub delta_hash: Value<F>,
    /// Current weights hash (public, verified against)
    pub current_hash: Value<F>,
}

impl<F: PrimeField> Circuit<F> for ProofOfLineageCircuit<F> {
    type Config = LineageConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(_meta: &mut ConstraintSystem<F>) -> Self::Config {
        // TODO: Hash combination gate: H(parent || delta) == current
        LineageConfig {}
    }

    fn synthesize(
        &self,
        _config: Self::Config,
        _layouter: impl Layouter<F>,
    ) -> Result<(), Error> {
        // TODO: Load parent_hash, delta_hash, compute combined hash, verify
        Ok(())
    }
}
