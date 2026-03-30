//! ProofOfNonRegression circuit — proves auxiliary scores didn't drop below threshold.

use halo2_proofs::circuit::{Layouter, SimpleFloorPlanner, Value};
use halo2_proofs::plonk::{Circuit, ConstraintSystem, Error};
use ff::PrimeField;

#[derive(Clone, Debug)]
pub struct NonRegressionConfig {
    // TODO: Define columns
}

#[derive(Clone, Debug, Default)]
pub struct ProofOfNonRegressionCircuit<F: PrimeField> {
    /// Auxiliary benchmark scores (private)
    pub aux_scores: Vec<Value<F>>,
    /// Minimum threshold (public)
    pub threshold: Value<F>,
}

impl<F: PrimeField> Circuit<F> for ProofOfNonRegressionCircuit<F> {
    type Config = NonRegressionConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(_meta: &mut ConstraintSystem<F>) -> Self::Config {
        // TODO: Range check gates: each aux_score >= threshold
        NonRegressionConfig {}
    }

    fn synthesize(
        &self,
        _config: Self::Config,
        _layouter: impl Layouter<F>,
    ) -> Result<(), Error> {
        // TODO: Load scores, verify each >= threshold
        Ok(())
    }
}
