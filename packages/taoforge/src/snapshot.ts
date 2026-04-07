import { MetagraphSnapshot } from "./types.js";

const SNAPSHOT_URLS: Record<number, string> = {
  1: "https://raw.githubusercontent.com/taoforge/taoforge-web/main/public/data/snapshots/sn1_sample.json",
  5: "https://raw.githubusercontent.com/taoforge/taoforge-web/main/public/data/snapshots/sn5_sample.json",
};

// Minimal fallback snapshot so the package works offline
const FALLBACK_SNAPSHOT: MetagraphSnapshot = {
  netuid: 1,
  block: 4200000,
  timestamp: Date.now() / 1000,
  neurons: Array.from({ length: 20 }, (_, i) => ({
    uid: i,
    stake: Math.random() * 10000,
    rank: Math.random(),
    trust: Math.random(),
    incentive: Math.random() * 0.1,
    emission: Math.random() * 1000,
    is_validator: i < 5,
    active: true,
  })),
};

export async function fetchSnapshot(netuid: number): Promise<MetagraphSnapshot> {
  const url = SNAPSHOT_URLS[netuid];
  if (!url) return { ...FALLBACK_SNAPSHOT, netuid };
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json() as MetagraphSnapshot;
  } catch {
    return { ...FALLBACK_SNAPSHOT, netuid };
  }
}

export function summarizeSnapshot(snapshot: MetagraphSnapshot): string {
  const neurons = snapshot.neurons;
  const validators = neurons.filter(n => n.is_validator);
  const totalStake = neurons.reduce((s, n) => s + n.stake, 0);
  const top5 = [...neurons].sort((a, b) => b.stake - a.stake).slice(0, 5);
  const gini = computeGini(neurons.map(n => n.stake));
  return [
    `Subnet SN${snapshot.netuid} | Block ${snapshot.block} | ${neurons.length} neurons`,
    `Validators: ${validators.length} | Total stake: ${totalStake.toFixed(0)} τ`,
    `Gini coefficient: ${gini.toFixed(4)} (stake concentration)`,
    `Top 5 by stake: ${top5.map(n => `UID${n.uid}(${n.stake.toFixed(0)}τ)`).join(", ")}`,
    `Active neurons: ${neurons.filter(n => n.active).length}/${neurons.length}`,
  ].join("\n");
}

function computeGini(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;
  const sum = sorted.reduce((s, v) => s + v, 0);
  if (sum === 0) return 0;
  let numerator = 0;
  for (let i = 0; i < n; i++) numerator += (2 * (i + 1) - n - 1) * sorted[i];
  return numerator / (n * sum);
}
