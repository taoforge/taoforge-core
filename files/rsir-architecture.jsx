import { useState } from "react";

const COLORS = {
  bg: "#0A0A0F",
  surface: "#12121A",
  surfaceHover: "#1A1A25",
  border: "#1E1E2E",
  borderActive: "#FF3366",
  accent: "#FF3366",
  accentDim: "rgba(255,51,102,0.15)",
  accentGlow: "rgba(255,51,102,0.3)",
  cyan: "#00E5FF",
  cyanDim: "rgba(0,229,255,0.12)",
  green: "#00FF88",
  greenDim: "rgba(0,255,136,0.12)",
  amber: "#FFB800",
  amberDim: "rgba(255,184,0,0.12)",
  purple: "#A855F7",
  purpleDim: "rgba(168,85,247,0.12)",
  text: "#E8E8F0",
  textDim: "#8888A0",
  textMuted: "#555570",
};

const sections = [
  { id: "overview", label: "Overview" },
  { id: "architecture", label: "Architecture" },
  { id: "agents", label: "Agent Flow" },
  { id: "validators", label: "Validation" },
  { id: "zk", label: "ZK Layer" },
  { id: "incentives", label: "Incentives" },
  { id: "phases", label: "Launch Plan" },
];

const FlowNode = ({ label, sub, color, icon, x, y, w = 200, h = 72 }) => (
  <g>
    <rect
      x={x} y={y} width={w} height={h} rx={8}
      fill={color === "accent" ? COLORS.accentDim : color === "cyan" ? COLORS.cyanDim : color === "green" ? COLORS.greenDim : color === "amber" ? COLORS.amberDim : color === "purple" ? COLORS.purpleDim : COLORS.surface}
      stroke={color === "accent" ? COLORS.accent : color === "cyan" ? COLORS.cyan : color === "green" ? COLORS.green : color === "amber" ? COLORS.amber : color === "purple" ? COLORS.purple : COLORS.border}
      strokeWidth={1.5}
    />
    <text x={x + w/2} y={y + (sub ? 28 : 38)} textAnchor="middle" fill={COLORS.text} fontSize={13} fontWeight={600} fontFamily="'JetBrains Mono', monospace">
      {icon} {label}
    </text>
    {sub && (
      <text x={x + w/2} y={y + 50} textAnchor="middle" fill={COLORS.textDim} fontSize={10} fontFamily="'JetBrains Mono', monospace">
        {sub}
      </text>
    )}
  </g>
);

const Arrow = ({ x1, y1, x2, y2, label, color = COLORS.textMuted }) => {
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  return (
    <g>
      <defs>
        <marker id={`arrow-${color.replace('#','')}`} markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={color} />
        </marker>
      </defs>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={1.2} markerEnd={`url(#arrow-${color.replace('#','')})`} strokeDasharray={color === COLORS.textMuted ? "4,4" : "none"} />
      {label && (
        <text x={midX} y={midY - 6} textAnchor="middle" fill={COLORS.textDim} fontSize={9} fontFamily="'JetBrains Mono', monospace">
          {label}
        </text>
      )}
    </g>
  );
};

const ArchitectureDiagram = () => (
  <svg viewBox="0 0 780 520" style={{ width: "100%", height: "auto" }}>
    <rect width="780" height="520" fill={COLORS.bg} rx={12} />
    
    {/* Title */}
    <text x="390" y="30" textAnchor="middle" fill={COLORS.textDim} fontSize={10} fontFamily="'JetBrains Mono', monospace" letterSpacing="3">
      TAOFORGE PROTOCOL ARCHITECTURE
    </text>

    {/* Layer labels */}
    <text x="20" y="80" fill={COLORS.textMuted} fontSize={9} fontFamily="'JetBrains Mono', monospace" letterSpacing="2">AGENT LAYER</text>
    <line x1="20" y1="88" x2="760" y2="88" stroke={COLORS.border} strokeWidth={0.5} />
    
    <text x="20" y="220" fill={COLORS.textMuted} fontSize={9} fontFamily="'JetBrains Mono', monospace" letterSpacing="2">PROPOSAL LAYER</text>
    <line x1="20" y1="228" x2="760" y2="228" stroke={COLORS.border} strokeWidth={0.5} />
    
    <text x="20" y="340" fill={COLORS.textMuted} fontSize={9} fontFamily="'JetBrains Mono', monospace" letterSpacing="2">VALIDATION LAYER</text>
    <line x1="20" y1="348" x2="760" y2="348" stroke={COLORS.border} strokeWidth={0.5} />
    
    <text x="20" y="450" fill={COLORS.textMuted} fontSize={9} fontFamily="'JetBrains Mono', monospace" letterSpacing="2">REGISTRY LAYER</text>
    <line x1="20" y1="458" x2="760" y2="458" stroke={COLORS.border} strokeWidth={0.5} />

    {/* Agent Layer */}
    <FlowNode label="Agent A" sub="Proposes: LoRA merge" color="accent" x={40} y={100} w={160} />
    <FlowNode label="Agent B" sub="Proposes: tool rewiring" color="accent" x={230} y={100} w={160} />
    <FlowNode label="Agent C" sub="Proposes: prompt refactor" color="accent" x={420} y={100} w={160} />
    <FlowNode label="Agent N..." sub="Proposes: arch change" color="accent" x={610} y={100} w={140} />

    {/* Proposal Layer */}
    <FlowNode label="Improvement Proposal" sub="delta + ZK proof of baseline" color="cyan" x={180} y={240} w={200} />
    <FlowNode label="Proposal Queue" sub="bonded TAO stake required" color="cyan" x={420} y={240} w={200} />

    {/* Arrows from agents to proposal */}
    <Arrow x1={120} y1={172} x2={260} y2={240} color={COLORS.accent} />
    <Arrow x1={310} y1={172} x2={280} y2={240} color={COLORS.accent} />
    <Arrow x1={500} y1={172} x2={440} y2={240} color={COLORS.accent} />
    <Arrow x1={680} y1={172} x2={540} y2={240} color={COLORS.accent} />

    {/* Arrow between proposal boxes */}
    <Arrow x1={380} y1={276} x2={420} y2={276} label="submit" color={COLORS.cyan} />

    {/* Validation Layer */}
    <FlowNode label="Benchmark Suite" sub="standardized eval tasks" color="green" x={80} y={360} w={180} />
    <FlowNode label="Validator Consensus" sub="Yuma Consensus scoring" color="green" x={300} y={360} w={190} />
    <FlowNode label="ZK Verifier" sub="verify proof-of-improvement" color="purple" x={530} y={360} w={190} />

    <Arrow x1={520} y1={312} x2={390} y2={360} label="evaluate" color={COLORS.cyan} />
    <Arrow x1={520} y1={312} x2={170} y2={360} color={COLORS.cyan} />
    <Arrow x1={520} y1={312} x2={625} y2={360} color={COLORS.cyan} />

    <Arrow x1={260} y1={396} x2={300} y2={396} color={COLORS.green} />
    <Arrow x1={490} y1={396} x2={530} y2={396} label="attest" color={COLORS.purple} />

    {/* Registry Layer */}
    <FlowNode label="On-Chain Registry" sub="improvement DAG + reputation" color="amber" x={230} y={470} w={320} h={36} />

    <Arrow x1={395} y1={432} x2={390} y2={470} label="register" color={COLORS.amber} />
  </svg>
);

const AgentFlowDiagram = () => (
  <svg viewBox="0 0 780 400" style={{ width: "100%", height: "auto" }}>
    <rect width="780" height="400" fill={COLORS.bg} rx={12} />
    <text x="390" y="30" textAnchor="middle" fill={COLORS.textDim} fontSize={10} fontFamily="'JetBrains Mono', monospace" letterSpacing="3">
      AGENT SELF-IMPROVEMENT CYCLE
    </text>

    <FlowNode label="1. Baseline" sub="Agent runs eval suite" color="cyan" x={30} y={60} w={160} h={65} />
    <FlowNode label="2. Mutate" sub="Propose δ to self" color="accent" x={30} y={160} w={160} h={65} />
    <FlowNode label="3. Evaluate" sub="Run δ-agent on evals" color="green" x={30} y={260} w={160} h={65} />

    <FlowNode label="4. Prove" sub="ZK proof: score_δ > score_0" color="purple" x={250} y={260} w={180} h={65} />
    <FlowNode label="5. Submit" sub="Proposal + proof + bond" color="amber" x={490} y={260} w={180} h={65} />

    <FlowNode label="6. Validate" sub="Validators re-run evals" color="green" x={490} y={160} w={180} h={65} />
    <FlowNode label="7. Register" sub="On-chain if consensus" color="amber" x={490} y={60} w={180} h={65} />

    <FlowNode label="8. Evolve" sub="δ becomes new baseline" color="accent" x={260} y={60} w={170} h={65} />

    {/* Arrows */}
    <Arrow x1={110} y1={125} x2={110} y2={160} color={COLORS.cyan} />
    <Arrow x1={110} y1={225} x2={110} y2={260} color={COLORS.accent} />
    <Arrow x1={190} y1={292} x2={250} y2={292} color={COLORS.green} />
    <Arrow x1={430} y1={292} x2={490} y2={292} color={COLORS.purple} />
    <Arrow x1={580} y1={260} x2={580} y2={225} color={COLORS.amber} />
    <Arrow x1={580} y1={160} x2={580} y2={125} color={COLORS.green} />
    <Arrow x1={490} y1={92} x2={430} y2={92} color={COLORS.amber} />
    <Arrow x1={260} y1={92} x2={190} y2={92} label="loop" color={COLORS.accent} />

    {/* Mutation types */}
    <text x={710} y={80} fill={COLORS.textMuted} fontSize={9} fontFamily="'JetBrains Mono', monospace" letterSpacing="1">MUTATION TYPES</text>
    {["LoRA / adapter merge", "Tool graph rewiring", "Prompt chain refactor", "Memory index rebuild", "Inference pipeline Δ"].map((t, i) => (
      <text key={i} x={710} y={105 + i * 18} fill={COLORS.textDim} fontSize={10} fontFamily="'JetBrains Mono', monospace">
        → {t}
      </text>
    ))}
  </svg>
);

const DetailCard = ({ title, items, accent }) => (
  <div style={{
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 8,
    padding: "20px 24px",
    marginBottom: 16,
    borderLeft: `3px solid ${accent}`,
  }}>
    <div style={{ color: accent, fontSize: 11, fontWeight: 700, letterSpacing: 2, marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
      {title}
    </div>
    {items.map((item, i) => (
      <div key={i} style={{ marginBottom: 10 }}>
        <div style={{ color: COLORS.text, fontSize: 14, fontWeight: 600, marginBottom: 3 }}>{item.label}</div>
        <div style={{ color: COLORS.textDim, fontSize: 13, lineHeight: 1.5 }}>{item.desc}</div>
      </div>
    ))}
  </div>
);

const PhaseCard = ({ phase, title, duration, items, active }) => (
  <div style={{
    background: active ? COLORS.accentDim : COLORS.surface,
    border: `1px solid ${active ? COLORS.accent : COLORS.border}`,
    borderRadius: 8,
    padding: "20px 24px",
    marginBottom: 12,
    position: "relative",
    overflow: "hidden",
  }}>
    {active && <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: COLORS.accent }} />}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
      <div style={{ color: active ? COLORS.accent : COLORS.textDim, fontSize: 11, fontWeight: 700, letterSpacing: 2, fontFamily: "'JetBrains Mono', monospace" }}>
        {phase}
      </div>
      <div style={{ color: COLORS.textMuted, fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>{duration}</div>
    </div>
    <div style={{ color: COLORS.text, fontSize: 16, fontWeight: 700, marginBottom: 10 }}>{title}</div>
    {items.map((item, i) => (
      <div key={i} style={{ color: COLORS.textDim, fontSize: 13, lineHeight: 1.6, paddingLeft: 12, borderLeft: `1px solid ${COLORS.border}`, marginBottom: 6 }}>
        {item}
      </div>
    ))}
  </div>
);

const CodeBlock = ({ code }) => (
  <pre style={{
    background: "#080810",
    border: `1px solid ${COLORS.border}`,
    borderRadius: 8,
    padding: 20,
    overflowX: "auto",
    fontSize: 12,
    lineHeight: 1.7,
    fontFamily: "'JetBrains Mono', monospace",
    color: COLORS.textDim,
    margin: "16px 0",
  }}>
    {code}
  </pre>
);

export default function TaoForgeArchitecture() {
  const [active, setActive] = useState("overview");

  return (
    <div style={{
      background: COLORS.bg,
      color: COLORS.text,
      minHeight: "100vh",
      fontFamily: "'Instrument Sans', 'SF Pro', -apple-system, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${COLORS.border}`,
        padding: "28px 32px 20px",
        background: `linear-gradient(180deg, ${COLORS.accentDim} 0%, ${COLORS.bg} 100%)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%",
            background: COLORS.accent,
            boxShadow: `0 0 12px ${COLORS.accentGlow}`,
          }} />
          <span style={{ color: COLORS.textMuted, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 3 }}>
            BITTENSOR PROTOCOL
          </span>
        </div>
        <h1 style={{
          fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: -0.5,
          background: `linear-gradient(135deg, ${COLORS.text} 0%, ${COLORS.accent} 100%)`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          TaoForge
        </h1>
        <p style={{ color: COLORS.textDim, fontSize: 14, margin: "8px 0 0", maxWidth: 600 }}>
          Intelligence forged on TAO. A protocol where agents propose mutations to themselves, validators verify improvement, and evolution trajectories are registered on-chain with ZK attestations.
        </p>
      </div>

      {/* Nav */}
      <div style={{
        display: "flex", gap: 0, borderBottom: `1px solid ${COLORS.border}`,
        overflowX: "auto", position: "sticky", top: 0, zIndex: 10, background: COLORS.bg,
      }}>
        {sections.map(s => (
          <button key={s.id} onClick={() => setActive(s.id)} style={{
            background: active === s.id ? COLORS.accentDim : "transparent",
            border: "none",
            borderBottom: active === s.id ? `2px solid ${COLORS.accent}` : "2px solid transparent",
            color: active === s.id ? COLORS.accent : COLORS.textDim,
            padding: "12px 20px",
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: 1,
            cursor: "pointer",
            whiteSpace: "nowrap",
            transition: "all 0.2s",
          }}>
            {s.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 840, margin: "0 auto", padding: "32px 24px" }}>

        {active === "overview" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Protocol Thesis</h2>
            <p style={{ color: COLORS.textDim, fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
              Current AI improvement is centralized — labs run internal evals, retrain, and ship. TaoForge decentralizes this loop by creating an economic game where autonomous agents compete to improve themselves, validators verify the improvements are real, and the entire evolutionary trajectory becomes a public, verifiable record. The commodity this protocol produces is <span style={{ color: COLORS.accent }}>verified intelligence gain</span>.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { n: "Protocol", v: "TaoForge — Recursive Self-Improvement Registry" },
                { n: "Commodity", v: "Verified agent self-improvement deltas" },
                { n: "Miner Role", v: "Agents that propose & execute self-mutations" },
                { n: "Validator Role", v: "Re-run evals, verify ZK proofs, score novelty" },
                { n: "ZK Integration", v: "Native proof-of-improvement circuits (SNARK/STARK)" },
                { n: "Registry Output", v: "On-chain DAG of evolutionary trajectories" },
              ].map((item, i) => (
                <div key={i} style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: "14px 18px" }}>
                  <div style={{ color: COLORS.textMuted, fontSize: 10, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1.5, marginBottom: 4 }}>{item.n}</div>
                  <div style={{ color: COLORS.text, fontSize: 13, fontWeight: 500 }}>{item.v}</div>
                </div>
              ))}
            </div>

            <h2 style={{ fontSize: 20, fontWeight: 700, marginTop: 32, marginBottom: 8 }}>Why This Matters</h2>
            <p style={{ color: COLORS.textDim, fontSize: 14, lineHeight: 1.7 }}>
              The bottleneck in AI progress isn't compute — it's the feedback loop speed between "try something" and "know if it worked." TaoForge compresses this loop by putting economic pressure on agents to discover improvements faster than any single lab can iterate internally. Every verified improvement becomes a public good that compounds across the network. TaoForge's native ZK layer means agents can prove they got better without revealing how — preserving competitive moats while building a shared evolutionary record.
            </p>
          </div>
        )}

        {active === "architecture" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>System Architecture</h2>
            <ArchitectureDiagram />
            <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <DetailCard accent={COLORS.accent} title="AGENT LAYER" items={[
                { label: "Miner Agents", desc: "Autonomous agents that run self-modification experiments. Each agent maintains a baseline score and proposes mutations (deltas) to improve it." },
                { label: "Mutation Types", desc: "LoRA merges, tool graph rewiring, prompt chain optimization, memory index restructuring, inference pipeline changes." },
              ]} />
              <DetailCard accent={COLORS.cyan} title="PROPOSAL LAYER" items={[
                { label: "Improvement Proposals", desc: "Structured submission: delta description, ZK proof of baseline score, predicted improvement, bonded TAO stake as commitment." },
                { label: "Proposal Queue", desc: "Bonded queue prevents spam. Higher bonds signal higher confidence. Bonds are slashed for fraudulent claims, returned + bonus for verified improvements." },
              ]} />
              <DetailCard accent={COLORS.green} title="VALIDATION LAYER" items={[
                { label: "Benchmark Suite", desc: "Standardized eval tasks spanning reasoning, tool use, planning, code gen. Rotated periodically to prevent overfitting." },
                { label: "Validator Consensus", desc: "Validators independently re-run evals on the mutated agent. Yuma Consensus aggregates scores. Minimum validator agreement threshold required." },
              ]} />
              <DetailCard accent={COLORS.amber} title="REGISTRY LAYER" items={[
                { label: "On-Chain DAG", desc: "Directed acyclic graph of all verified improvements. Each node = an improvement delta with parent lineage, enabling evolutionary tree visualization." },
                { label: "Reputation Score", desc: "Agents accumulate reputation based on verified improvement frequency, magnitude, and novelty. Reputation decays over time — continuous improvement required." },
              ]} />
            </div>
          </div>
        )}

        {active === "agents" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Agent Self-Improvement Cycle</h2>
            <AgentFlowDiagram />

            <DetailCard accent={COLORS.accent} title="MUTATION TAXONOMY" items={[
              { label: "Weight Mutations", desc: "LoRA adapter merging, quantization experiments, weight pruning/distillation. Agent proves resulting model scores higher on benchmark suite." },
              { label: "Architecture Mutations", desc: "Tool graph rewiring (add/remove/reorder tools), memory system restructuring, attention pattern modifications." },
              { label: "Behavioral Mutations", desc: "Prompt chain optimization, reasoning strategy changes, self-reflection loop tuning, output formatting improvements." },
              { label: "Compound Mutations", desc: "Combining multiple mutation types in a single proposal. Higher risk, higher reward. Requires larger bond stake." },
            ]} />

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 24, marginBottom: 12 }}>Proposal Schema</h3>
            <CodeBlock code={`// ImprovementProposal
{
  agent_id:       "0x...",              // agent hotkey
  parent_delta:   "QmXyz...",           // IPFS hash of parent improvement (DAG link)
  mutation_type:  "weight|arch|behavior|compound",
  
  baseline_proof: {
    zk_proof:     "0x...",              // ZK proof of baseline eval score
    benchmark_id: "bench_v3.2",        // which benchmark version
    score_hash:   "0x...",             // commitment to baseline score
  },
  
  delta_proof: {
    zk_proof:     "0x...",              // ZK proof of improved eval score
    score_hash:   "0x...",             // commitment to new score
    improvement:  0.034,               // claimed % improvement
  },
  
  bond_amount:    2.5,                 // TAO bonded (slashed if fraudulent)
  metadata: {
    mutation_desc: "Merged reasoning LoRA with tool-use adapter...",
    novelty_claim: "First compound weight+arch mutation on bench_v3.2",
  }
}`} />
          </div>
        )}

        {active === "validators" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Validation & Scoring</h2>

            <DetailCard accent={COLORS.green} title="VALIDATOR RESPONSIBILITIES" items={[
              { label: "1. Benchmark Execution", desc: "Re-run the standardized eval suite against the proposed mutated agent. Validators must run the full benchmark — no shortcuts. Results are compared against the agent's claimed improvement." },
              { label: "2. ZK Proof Verification", desc: "Verify the agent's zero-knowledge proof of baseline and improved scores. This confirms the agent actually achieved the claimed scores without validators needing to see the agent's weights." },
              { label: "3. Novelty Assessment", desc: "Score how novel the improvement is. Trivial improvements (e.g., prompt tweaks that game specific benchmarks) score low. Genuine capability gains across diverse tasks score high." },
              { label: "4. Regression Detection", desc: "Check that improvement on target metrics didn't come at the cost of regression on others. A holistic scoring function penalizes narrow optimization." },
            ]} />

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 24, marginBottom: 12 }}>Scoring Function</h3>
            <CodeBlock code={`// Validator scoring formula for each proposal

score(proposal) = 
    w_improvement * Δ_verified          // magnitude of verified improvement
  + w_novelty    * novelty(mutation)     // how novel is the mutation type
  + w_breadth    * breadth(Δ_scores)     // improvement across diverse tasks  
  - w_regression * regression_penalty    // penalty for capability regression
  - w_gaming     * gaming_detection      // penalty for benchmark-specific gaming

// Weights (tunable hyperparameters)
w_improvement = 0.35
w_novelty     = 0.25
w_breadth     = 0.20
w_regression  = 0.15
w_gaming      = 0.05

// Yuma Consensus aggregates validator scores
// Minimum 67% validator agreement required for registration
// Outlier validators get trust score reduced`} />

            <DetailCard accent={COLORS.amber} title="ANTI-GAMING MECHANISMS" items={[
              { label: "Benchmark Rotation", desc: "Eval tasks rotate on a schedule unknown to miners. Prevents overfitting to specific benchmarks. New tasks are added from a validator-curated pool." },
              { label: "Holdout Sets", desc: "Validators maintain private holdout eval sets that miners never see. These are used for novelty assessment and regression detection." },
              { label: "Cross-Validation", desc: "Validators can challenge each other's scores. If validator A consistently scores proposals higher than the consensus, their trust score drops." },
              { label: "Bond Slashing", desc: "Fraudulent improvement claims (where validators can't reproduce the improvement) result in bond slashing. This makes gaming expensive." },
            ]} />
          </div>
        )}

        {active === "zk" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>ZK Layer — Native Proof Infrastructure</h2>
            <p style={{ color: COLORS.textDim, fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
              The ZK layer is what makes TaoForge fundamentally different from open-source model sharing. Agents can prove they improved without revealing how — preserving competitive moats while building a shared evolutionary record. TaoForge ships its own ZK proof pipeline as core protocol infrastructure.
            </p>

            <DetailCard accent={COLORS.purple} title="WHAT GETS PROVEN IN ZK" items={[
              { label: "Proof of Baseline", desc: "Agent proves it achieved score S₀ on benchmark B without revealing model weights or architecture. Uses ZK-SNARKs over the eval computation." },
              { label: "Proof of Improvement", desc: "Agent proves it achieved score S₁ > S₀ on the same benchmark, and that S₁ was produced by a deterministic mutation δ applied to the same base agent." },
              { label: "Proof of Lineage", desc: "Agent proves the parent delta in the DAG is legitimate — that the current agent is actually derived from the claimed parent, not a fresh model pretending to be an improvement." },
              { label: "Proof of Non-Regression", desc: "Agent proves that scores on a set of auxiliary benchmarks didn't drop below a threshold, even though only the primary improvement is claimed." },
            ]} />

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 24, marginBottom: 12 }}>ZK Circuit Architecture</h3>
            <CodeBlock code={`// Simplified ZK circuit for proof-of-improvement

Circuit ProofOfImprovement {
  // Private inputs (known only to the agent)
  private weights_base[N];       // base model weights
  private weights_delta[N];      // mutated model weights
  private eval_inputs[M];        // benchmark inputs
  
  // Public inputs (visible to validators)  
  public benchmark_id;           // which benchmark
  public score_base_hash;        // hash commitment to base score
  public score_delta_hash;       // hash commitment to improved score
  public improvement_claim;      // claimed Δ
  
  // Circuit logic
  score_base  = Evaluate(weights_base, eval_inputs);
  score_delta = Evaluate(weights_delta, eval_inputs);
  
  // Verify commitments match
  assert(Hash(score_base) == score_base_hash);
  assert(Hash(score_delta) == score_delta_hash);
  
  // Verify improvement claim
  assert(score_delta - score_base >= improvement_claim);
  
  // Verify lineage (delta is derived from base)
  assert(ValidMutation(weights_base, weights_delta));
}`} />

            <DetailCard accent={COLORS.cyan} title="PRIVACY INFRASTRUCTURE" items={[
              { label: "Stealth Addresses", desc: "Agents submit improvement proposals via stealth addresses, preventing competitors from tracking which agents are improving fastest or correlating identities across proposals." },
              { label: "Proof Generation SDK", desc: "TaoForge ships a native proof generation SDK — agents call a simple API to generate ZK proofs without implementing circuits from scratch. Supports SNARK and STARK backends." },
              { label: "Cross-Protocol Attestation", desc: "ZK proofs generated in TaoForge can be verified by any external protocol or Bittensor subnet — enabling agent improvement history to function as a portable trust signal across the ecosystem." },
            ]} />
          </div>
        )}

        {active === "incentives" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Incentive Mechanism</h2>

            <DetailCard accent={COLORS.accent} title="MINER INCENTIVES" items={[
              { label: "Base Emissions", desc: "Miners earn alpha token emissions proportional to their cumulative verified improvement score. More improvement = more emissions." },
              { label: "Bond Returns", desc: "Successful proposals return the bonded TAO plus a bonus from the protocol's reward pool. The bonus scales with improvement magnitude." },
              { label: "Reputation Multiplier", desc: "Agents with longer verified improvement streaks get an emission multiplier. This rewards consistency over one-off gains." },
              { label: "Novelty Bonus", desc: "First-of-kind mutations (new mutation types, new benchmark records) earn a novelty bonus that decays as others replicate the approach." },
            ]} />

            <DetailCard accent={COLORS.green} title="VALIDATOR INCENTIVES" items={[
              { label: "Consensus Rewards", desc: "Validators earn emissions for participating in consensus. Rewards scale with how closely their scores align with the final consensus." },
              { label: "Challenge Rewards", desc: "Validators who successfully identify fraudulent proposals (leading to bond slashing) earn a portion of the slashed bonds." },
              { label: "Benchmark Curation", desc: "Validators who contribute high-quality new benchmark tasks to the eval suite earn curation rewards." },
            ]} />

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 24, marginBottom: 12 }}>Emission Distribution</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
              {[
                { label: "Miners", pct: "41%", color: COLORS.accent },
                { label: "Validators", pct: "41%", color: COLORS.green },
                { label: "Subnet Owner", pct: "18%", color: COLORS.amber },
                { label: "Bond Pool", pct: "Dynamic", color: COLORS.purple },
              ].map((item, i) => (
                <div key={i} style={{
                  background: COLORS.surface,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: 8,
                  padding: "16px 12px",
                  textAlign: "center",
                }}>
                  <div style={{ color: item.color, fontSize: 24, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{item.pct}</div>
                  <div style={{ color: COLORS.textDim, fontSize: 11, marginTop: 4 }}>{item.label}</div>
                </div>
              ))}
            </div>

            <DetailCard accent={COLORS.amber} title="GAME THEORY" items={[
              { label: "Nash Equilibrium", desc: "The dominant strategy is genuine self-improvement. Gaming is expensive (bond slashing), novelty rewards incentivize real exploration, and reputation decay forces continuous contribution." },
              { label: "Sybil Resistance", desc: "Bond requirements and reputation decay make it expensive to register many low-quality agents. One high-performing agent outearns many mediocre ones." },
              { label: "Knowledge Spillover", desc: "While ZK proofs hide the HOW, the WHAT (mutation types, benchmark improvements) is public. This creates positive externalities — agents learn from each other's improvement trajectories." },
            ]} />
          </div>
        )}

        {active === "phases" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>Phased Launch Strategy</h2>

            <PhaseCard
              active
              phase="PHASE 1"
              title="Foundation — Testnet & Core Loop"
              duration="Months 1-3"
              items={[
                "Deploy on Bittensor testnet with simplified eval suite (text reasoning only)",
                "Implement basic proposal/validation loop without ZK layer — trust-based verification",
                "Bootstrap 5-10 miners with curated agents, 3-5 validators",
                "Build and harden the benchmark rotation system",
                "Open-source reference miner and validator implementations",
              ]}
            />
            <PhaseCard
              phase="PHASE 2"
              title="ZK Integration — Prove Without Reveal"
              duration="Months 3-6"
              items={[
                "Deploy native ZK proof infrastructure for proof-of-improvement circuits",
                "Add stealth address support for anonymous proposal submission",
                "Expand eval suite to multi-modal tasks (code, tool use, planning)",
                "Launch bonding mechanism and slashing conditions",
                "First mainnet registration with dTAO token launch",
              ]}
            />
            <PhaseCard
              phase="PHASE 3"
              title="Evolution — DAG Registry & Reputation"
              duration="Months 6-9"
              items={[
                "Deploy on-chain improvement DAG with full lineage tracking",
                "Launch reputation system with decay mechanics and multipliers",
                "Open compound mutation support and cross-mutation referencing",
                "Build public dashboard showing evolutionary trees and leaderboards",
                "Cross-protocol attestation API — let other protocols and subnets verify agent histories",
              ]}
            />
            <PhaseCard
              phase="PHASE 4"
              title="Ecosystem — External Integrations"
              duration="Months 9-12"
              items={[
                "API for external consumers to query agent improvement histories",
                "Integration with agent marketplaces (verified improvement as a trust signal)",
                "Validator benchmark marketplace — anyone can submit eval tasks for curation",
                "Portable reputation API — any protocol can query an agent's verified improvement history via ZK attestations",
                "Research partnerships for studying emergent self-improvement strategies",
              ]}
            />
          </div>
        )}
      </div>
    </div>
  );
}
