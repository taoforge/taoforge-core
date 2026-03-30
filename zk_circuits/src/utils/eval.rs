//! Eval computation gadget — represents evaluation trace in constraints.
//!
//! In practice, fully re-executing an AI eval inside a ZK circuit is
//! impractical. Instead, we commit to the evaluation trace and verify
//! key properties (score computation from outputs, deterministic execution).

// TODO: Implement eval trace commitment scheme.
//
// Approach: Rather than proving the full eval computation in-circuit,
// the agent commits to:
// 1. Hash of all eval inputs
// 2. Hash of all eval outputs
// 3. Score computation from outputs (this part IS in-circuit)
//
// The verifier checks:
// 1. Input hash matches the benchmark version
// 2. Output hash is consistent with the committed score
// 3. Score computation is correct
//
// This is a "commit-and-prove" approach that makes the circuit
// tractable while still providing meaningful guarantees.
