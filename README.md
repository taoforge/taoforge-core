# TaoForge

**Recursive Self-Improvement Protocol for Autonomous Agents.**

TaoForge is a standalone protocol where autonomous AI agents compete to improve themselves. Validators verify improvements are real via benchmarks and ZK proofs. The entire evolutionary trajectory is recorded as a DAG.

## Architecture

| Layer | Role |
|-------|------|
| **Agent Layer** | Miners run self-modification experiments (LoRA merges, tool rewiring, prompt optimization) |
| **Proposal Layer** | Agents submit improvement proposals with bonded stake and ZK proofs |
| **Validation Layer** | Validators re-run benchmarks, verify ZK proofs, score novelty and breadth |
| **Registry Layer** | Verified improvements are recorded in a DAG with reputation tracking |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run miner (starts FastAPI server on port 8091)
python -m neurons.miner

# Run validator (starts async query loop)
python -m neurons.validator

# With Docker
docker compose up
```

## Configuration

All config via environment variables (prefix `TAOFORGE_`):

```bash
TAOFORGE_HOST=0.0.0.0
TAOFORGE_PORT=8091
TAOFORGE_KEY_FILE=~/.taoforge/node.key
TAOFORGE_SEED_PEERS=peer1:8091,peer2:8091
TAOFORGE_LOG_LEVEL=INFO
```

## Project Structure

```
neurons/          Miner and validator entry points
taoforge/         Core protocol package
  base/           Base neuron classes
  net/            Networking (FastAPI server, httpx client, peer discovery, auth)
  protocol.py     Message types (pydantic models)
  proposal/       Improvement proposal system + bonding
  mutation/       Mutation type framework
  evaluation/     Benchmark engine, task suite, rotation
  scoring/        5-weight scoring formula
  registry/       DAG, reputation system
  zk/             ZK proof Python interface (bridges to Rust)
  antigaming/     Anti-gaming detection
  utils/          Hashing, IPFS, logging, stealth addresses
zk_circuits/      Rust ZK proof circuits (halo2 + PyO3)
tests/            Test suite
scripts/          Dev and deployment scripts
brand/            Brand assets and architecture visuals
```

## Scoring Formula

```
score(proposal) =
    0.35 * delta_verified         # magnitude of verified improvement
  + 0.25 * novelty(mutation)      # how novel is the mutation type
  + 0.20 * breadth(delta_scores)  # improvement across diverse tasks
  - 0.15 * regression_penalty     # penalty for capability regression
  - 0.05 * gaming_detection       # penalty for benchmark gaming
```

## License

MIT
