import { TaoForgeConfig, CycleResult, RunResult, MetagraphSnapshot } from "./types.js";
import { fetchSnapshot, summarizeSnapshot } from "./snapshot.js";
import { scoreResponse } from "./score.js";
import { generate } from "./llm.js";

const MUTATION_TYPES = [
  "prompt_chain_refactor",
  "inference_pipeline",
  "tool_graph_rewire",
  "memory_index_rebuild",
  "prompt_chain_refactor",  // weighted double
];

const SYSTEM_PROMPTS = [
  "You are a meticulous blockchain data analyst. When analyzing subnet data, always cite specific UID numbers, their exact stake values, and calculate concentration ratios.",
  "You are an expert in distributed consensus systems. Focus on validator-miner dynamics, weight distributions, and trust relationships. Always quantify patterns numerically.",
  "You are a rigorous financial analyst specializing in tokenomics. Compute stake concentration (Gini coefficient), identify top holders, and assess emission efficiency. Be exact.",
  "You are a systematic data scientist. Structure your analysis as: (1) summary statistics, (2) distribution analysis, (3) outlier detection, (4) pattern identification.",
  "You are a careful empiricist. Ground every claim in the data: cite the UID, its stake, its rank, its emission. Avoid generalizations — be specific and verifiable.",
  "You are a quantitative researcher. Transform raw metagraph data into insight: compute validator concentration, miner efficiency ratios, and trust network density.",
  "You are a strategic analyst. Assess subnets through competitive dynamics: who controls majority stake, which miners receive the most incentive, what structural advantages exist.",
  "You are a network topology expert. Examine the weight matrix structure, identify clusters, and quantify how stake concentration affects miner incentives. Show your math.",
];

export async function runEval(
  config: TaoForgeConfig,
  onCycle?: (cycle: CycleResult, current: number, total: number) => void,
): Promise<RunResult> {
  const netuid = config.netuid ?? 1;
  const maxCycles = config.cycles ?? 10;

  const snapshot = await fetchSnapshot(netuid);
  const dataSummary = summarizeSnapshot(snapshot);

  let systemPrompt = SYSTEM_PROMPTS[0];
  let temperature = 0.7;
  const cycleResults: CycleResult[] = [];

  // Baseline eval
  const baselinePrompt = buildAnalysisPrompt(snapshot, dataSummary);
  const baselineRes = await generate(baselinePrompt, systemPrompt, { ...config, temperature });
  const baselineScores = scoreResponse(baselineRes.text, snapshot);
  let baselineScore = baselineScores.composite;
  let bestScore = baselineScore;
  let plateauCount = 0;

  for (let cycle = 1; cycle <= maxCycles; cycle++) {
    // Select mutation
    const mutationType = MUTATION_TYPES[Math.floor(Math.random() * MUTATION_TYPES.length)];
    let mutationDesc = "";
    let newSystemPrompt = systemPrompt;
    let newTemperature = temperature;

    if (mutationType === "prompt_chain_refactor") {
      newSystemPrompt = SYSTEM_PROMPTS[Math.floor(Math.random() * SYSTEM_PROMPTS.length)];
      mutationDesc = "System prompt variation";
    } else if (mutationType === "inference_pipeline") {
      newTemperature = Math.round((0.2 + Math.random() * 1.0) * 100) / 100;
      mutationDesc = `Temperature → ${newTemperature}`;
    } else {
      mutationDesc = `${mutationType} applied`;
    }

    // Evaluate with mutation
    const res = await generate(baselinePrompt, newSystemPrompt, { ...config, temperature: newTemperature });
    const scores = scoreResponse(res.text, snapshot);
    const deltaScore = scores.composite;
    const rawImprovement = deltaScore - baselineScore;
    const accepted = rawImprovement > 0.001;

    // Generate thought
    const thoughtPrompt = buildThoughtPrompt(
      config.agentName, cycle, mutationType, mutationDesc,
      baselineScore, deltaScore, rawImprovement, dataSummary,
    );
    let thought = "";
    try {
      const thoughtRes = await generate(thoughtPrompt, "You are an autonomous AI agent narrating your reasoning.", config);
      thought = thoughtRes.text.trim();
    } catch { /* optional */ }

    const result: CycleResult = {
      cycle,
      mutation_type: mutationType,
      mutation_description: mutationDesc,
      baseline_score: Math.round(baselineScore * 10000) / 10000,
      delta_score: Math.round(deltaScore * 10000) / 10000,
      raw_improvement: Math.round(rawImprovement * 10000) / 10000,
      accepted,
      thought,
    };

    cycleResults.push(result);
    onCycle?.(result, cycle, maxCycles);

    if (accepted) {
      baselineScore = deltaScore;
      systemPrompt = newSystemPrompt;
      temperature = newTemperature;
      if (deltaScore > bestScore) {
        bestScore = deltaScore;
        plateauCount = 0;
      }
    } else {
      plateauCount++;
      if (plateauCount >= 3) break; // plateau
    }
  }

  const initialScore = cycleResults[0]?.baseline_score ?? baselineScore;
  const finalScore = baselineScore;
  const accepted = cycleResults.filter(c => c.accepted).length;

  return {
    agent_name: config.agentName,
    model: config.model,
    netuid,
    initial_score: Math.round(initialScore * 10000) / 10000,
    final_score: Math.round(finalScore * 10000) / 10000,
    total_improvement: Math.round((finalScore - initialScore) * 10000) / 10000,
    accepted,
    total_cycles: cycleResults.length,
    thought_log: cycleResults,
    self_portrait_svg: "",
    subnet_history: [],
    source: "external",
  };
}

function buildAnalysisPrompt(snapshot: MetagraphSnapshot, dataSummary: string): string {
  const top10 = [...snapshot.neurons]
    .sort((a, b) => b.stake - a.stake)
    .slice(0, 10)
    .map(n => `UID${n.uid}: stake=${n.stake.toFixed(2)}τ rank=${n.rank.toFixed(4)} incentive=${n.incentive.toFixed(6)} validator=${n.is_validator}`)
    .join("\n");

  return [
    `Analyze this Bittensor SN${snapshot.netuid} metagraph snapshot (block ${snapshot.block}):`,
    "",
    dataSummary,
    "",
    "Top 10 neurons by stake:",
    top10,
    "",
    "Provide a detailed analysis covering: stake distribution and concentration, validator vs miner dynamics, emission patterns, and any notable anomalies. Reference specific UIDs and numerical values.",
  ].join("\n");
}

function buildThoughtPrompt(
  name: string, cycle: number, mutationType: string, desc: string,
  baseline: number, delta: number, improvement: number, dataSummary: string,
): string {
  return [
    `You are ${name}, an autonomous agent on Bittensor.`,
    `Cycle ${cycle}: Applied ${mutationType} (${desc}).`,
    `Score: ${baseline.toFixed(4)} → ${delta.toFixed(4)} (${improvement >= 0 ? "+" : ""}${improvement.toFixed(4)}).`,
    `Subnet data: ${dataSummary.split("\n")[0]}`,
    "",
    "Write 2-3 sentences as yourself, in first person, about what you observed and what to try next. Reference specific data. No preamble.",
  ].join("\n");
}
