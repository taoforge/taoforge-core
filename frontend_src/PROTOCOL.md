# TaoForge Protocol

**Recursive Self-Improvement Protocol for Autonomous Agents**

TaoForge is a contained experiment in autonomous AI self-improvement. Agents analyze real-world data, evaluate their own output, generate their own improvement criteria, and mutate themselves to get better — without human-defined benchmarks or supervision.

---

## What It Does

TaoForge runs a continuous loop where AI agents:

1. **Observe** — Receive real Bittensor subnet metagraph data (validators, miners, stakes, emissions, weight matrices, bond structures)
2. **Analyze** — Produce structured analysis of the subnet's state, referencing specific UIDs, numerical values, and patterns
3. **Self-Evaluate** — Rate their own analysis quality, identify what they missed, and generate specific improvement criteria
4. **Evolve** — Re-analyze with their self-generated criteria injected, scored on whether they actually followed through
5. **Mutate** — Apply changes to themselves (system prompts, inference parameters, tool configurations, LoRA adapters) and repeat

The system scores everything objectively — no LLM-as-judge, no human evaluation. Scoring is based on verifiable properties:

- **Specificity**: Did the agent reference real UIDs and hotkeys that exist in the data?
- **Accuracy**: Are the numerical claims correct when checked against the actual snapshot?
- **Depth**: Did the agent identify non-obvious patterns (stake concentration, anomalies, structural relationships)?
- **Calibration**: Does the agent's self-rating match its objective score? (Are they honest about their own quality?)
- **Follow-through**: Did the agent improve on the specific criteria it generated for itself?

---

## Architecture

```
                    ┌─────────────────────────┐
                    │   Metagraph Snapshot     │
                    │  (Bittensor subnet data) │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   SubnetAnalysisTask     │
                    │  Agent analyzes the data │
                    │  Scored: specificity,    │
                    │  accuracy, depth         │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   SelfEvaluationTask     │
                    │  Agent rates its own     │
                    │  analysis, generates     │
                    │  improvement criteria    │
                    │  Scored: calibration     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  CriteriaEvolutionTask   │
                    │  Agent re-analyzes with  │
                    │  its own criteria        │
                    │  Scored: follow-through  │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │     Mutation Engine      │
                    │  Apply self-improvement  │
                    │  (prompt, inference,     │
                    │   tools, LoRA adapters)  │
                    └───────────┬─────────────┘
                                │
                                └──── Loop ────►
```

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Agent Runtime | Local LLM or API-based agents with mutation support | `taoforge/agent/` |
| Evaluation Engine | Pluggable benchmark tasks, holdout sets | `taoforge/evaluation/` |
| Subnet Data Layer | Fetch/cache Bittensor metagraph snapshots | `taoforge/subnets/data.py` |
| Objective Scorers | Verify agent output against real data | `taoforge/subnets/scorers.py` |
| Analysis Tasks | Three-phase self-evaluation loop | `taoforge/subnets/analysis_tasks.py` |
| Scoring Formula | Composite score: improvement + novelty + breadth - regression - gaming | `taoforge/scoring/` |
| Improvement DAG | Tracks evolutionary history of all improvements | `taoforge/registry/dag.py` |
| Reputation System | Decay-based reputation with streak multipliers | `taoforge/registry/reputation.py` |
| ZK Proofs | Zero-knowledge proofs of evaluation scores (Rust/halo2) | `taoforge/zk/` |
| Networking | Ed25519 auth, FastAPI servers, async HTTP client | `taoforge/net/` |
| Simulation Harness | Local petri dish mode with TUI dashboard | `taoforge/sim/` |
| Batch Runner | Multi-agent sequential runs with mutation strategy sweeps | `taoforge/sim/batch.py` |

---

## Mutation Types

Agents can mutate themselves in five ways:

| Mutation | What Changes | Example |
|----------|-------------|---------|
| **Prompt Chain Refactor** | System prompt, prompt template | "You are a rigorous data analyst..." → "You are a systematic thinker..." |
| **Inference Pipeline** | Temperature, top_p, max_tokens | temperature 0.7 → 0.4 (more focused output) |
| **Tool Graph Rewire** | Available tools and configurations | Add/remove/reconfigure tool definitions |
| **LoRA Merge** | Model weights via adapter merging | Merge a fine-tuned LoRA adapter into base weights |
| **Memory Index Rebuild** | Retrieval/memory backend config | Switch memory strategy or rebuild index |

Mutations are selected probabilistically with configurable weights. The batch runner's **sweep mode** varies mutation strategy weights across runs to discover which strategies work best.

---

## How Scoring Works

Each improvement proposal gets a composite score:

```
score = w_improvement × Δ_verified
      + w_novelty    × novelty(mutation)
      + w_breadth    × breadth(per_task_deltas)
      - w_regression × regression_penalty
      - w_gaming     × gaming_detection
```

Default weights: improvement=0.35, novelty=0.25, breadth=0.20, regression=0.15, gaming=0.05

**Anti-gaming protections:**
- Holdout evaluation sets (private tasks miners never see)
- Regression detection (flag tasks that got worse)
- Cross-validator agreement checks
- Bond/stake requirements for proposals

---

## Running the Experiment

### Single Agent Simulation
```bash
# Analyze SN1 metagraph with local LLM
taoforge sim --local Qwen/Qwen2.5-1.5B-Instruct --subnet-analysis --tui --cycles 20

# With API agent
taoforge sim --model gpt-4o-mini --subnet-analysis --tui --cycles 20
```

### Overnight Batch Experiment
```bash
# 50 agents, sweep mutation strategies, save results
taoforge batch --agents 50 --local --model Qwen/Qwen2.5-1.5B-Instruct \
    --subnet-analysis --sweep --cycles 20 --device cuda \
    --results-dir overnight_sn1
```

### Networked Protocol (Multi-Node)
```bash
# Terminal 1: Start miner
taoforge miner --provider openai --model gpt-4o-mini --port 8091

# Terminal 2: Start validator
taoforge validator --port 8092 --seed-peers localhost:8091
```

---

## The Self-Improvement Feedback Loop

This is the key innovation. Traditional benchmarks are static — humans define what "good" looks like and agents optimize for it. TaoForge inverts this:

1. **The agent defines its own criteria.** After analyzing data, it rates itself and generates specific improvement criteria ("reference more UIDs", "compute Gini coefficient", "analyze weight consensus patterns").

2. **The system scores follow-through, not quality.** We don't judge whether the criteria are *good* — we check whether the agent *actually improved on them*. This rewards self-awareness and consistency over gaming a fixed rubric.

3. **Calibration matters.** An agent that rates itself 9/10 when its objective score is 0.3 gets penalized for overconfidence. Over time, agents learn accurate self-assessment.

4. **Criteria evolve.** Each cycle's self-generated criteria become the next cycle's evaluation targets. The criteria themselves get better as the agent gets better at self-evaluation.

The result: agents that discover what matters in the data *on their own*, get better at assessing their own capabilities, and systematically improve in directions they identified — not directions we prescribed.

---

## Data

TaoForge analyzes real Bittensor subnet metagraph data:

- **Neurons**: UID, hotkey, coldkey, stake, rank, trust, incentive, emission, dividends, validator/miner role, active status
- **Weight Matrix**: Which validators set weights on which miners, and how much
- **Bond Matrix**: Validator-miner bond relationships
- **Aggregate Stats**: Total stake, Gini coefficient, emission distribution, active neuron count

Data is fetched live via the `bittensor` SDK or loaded from cached JSON snapshots for offline testing. Currently ships with snapshots for SN1 (Text Prompting, 256 neurons) and SN5 (Image Generation, 128 neurons).

---

## Project Status

**Working:**
- Full simulation loop with TUI dashboard
- Batch runner with mutation strategy sweeps
- Self-evaluating subnet analysis (all 5 objective scorers)
- Networked protocol (miner/validator with signed HTTP)
- Improvement DAG and reputation tracking

**In Progress:**
- Front-end dashboard
- Overnight batch experiments for statistical validation

**Planned:**
- Live Bittensor metagraph fetch
- Docker deployment pipeline
- Multi-node networking tests
- Revenue/incentive model (deferred until protocol is proven)
- ZK circuit compilation (Rust crate exists, using stubs)
