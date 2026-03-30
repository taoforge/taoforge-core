//! ProofOfBaseline circuit — proves an agent achieved score S on benchmark B.
//!
//! Simpler than ProofOfImprovement — just a hash commitment to the score.

use halo2_proofs::circuit::{Layouter, SimpleFloorPlanner, Value};
use halo2_proofs::plonk::{Circuit, ConstraintSystem, Error};
use ff::PrimeField;

#[derive(Clone, Debug)]
pub struct BaselineConfig {
    // TODO: Define columns
}

#[derive(Clone, Debug, Default)]
pub struct ProofOfBaselineCircuit<F: PrimeField> {
    /// Baseline score (private)
    pub score: Value<F>,
    /// Score hash commitment (public, verified against)
    pub score_hash: Value<F>,
}

impl<F: PrimeField> Circuit<F> for ProofOfBaselineCircuit<F> {
    type Config = BaselineConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(_meta: &mut ConstraintSystem<F>) -> Self::Config {
        // TODO: Hash commitment gate
        BaselineConfig {}
    }

    fn synthesize(
        &self,
        _config: Self::Config,
        _layouter: impl Layouter<F>,
    ) -> Result<(), Error> {
        // TODO: Assign score, compute hash, verify commitment
        Ok(())
    }
}
