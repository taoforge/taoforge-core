export interface Neuron {
  uid: number;
  stake: number;
  rank: number;
  trust: number;
  incentive: number;
  emission: number;
  is_validator: boolean;
  active: boolean;
}

export interface MetagraphSnapshot {
  netuid: number;
  block: number;
  timestamp: number;
  neurons: Neuron[];
}

export interface CycleResult {
  cycle: number;
  mutation_type: string;
  mutation_description: string;
  baseline_score: number;
  delta_score: number;
  raw_improvement: number;
  accepted: boolean;
  thought: string;
}

export interface RunResult {
  agent_name: string;
  model: string;
  netuid: number;
  initial_score: number;
  final_score: number;
  total_improvement: number;
  accepted: number;
  total_cycles: number;
  thought_log: CycleResult[];
  self_portrait_svg: string;
  subnet_history: Array<{ netuid: number; cycle: number; score: number; reason: string }>;
  source: "external";
}

export interface TaoForgeConfig {
  agentName: string;
  model: string;
  apiKey: string;
  provider: "openai" | "anthropic";
  cycles?: number;
  netuid?: number;
  apiUrl?: string;
}
