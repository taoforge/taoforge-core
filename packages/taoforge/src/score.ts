import { MetagraphSnapshot } from "./types.js";

export function scoreResponse(
  response: string,
  snapshot: MetagraphSnapshot,
): { specificity: number; accuracy: number; depth: number; composite: number } {
  const neurons = snapshot.neurons;
  const totalStake = neurons.reduce((s, n) => s + n.stake, 0);

  // Specificity: mentions specific UID numbers present in the snapshot
  const uidMentions = neurons.filter(n =>
    response.includes(`UID${n.uid}`) ||
    response.includes(`uid ${n.uid}`) ||
    response.includes(`UID ${n.uid}`) ||
    new RegExp(`\\b${n.uid}\\b`).test(response)
  ).length;
  const specificity = Math.min(uidMentions / Math.max(neurons.length * 0.15, 3), 1);

  // Accuracy: numerical claims within 20% of actual values
  const numberPattern = /\b(\d+(?:\.\d+)?)\b/g;
  const mentionedNumbers = [...response.matchAll(numberPattern)].map(m => parseFloat(m[1]));
  const realValues = neurons.flatMap(n => [n.stake, n.incentive * 1000, n.emission]);
  let accurateHits = 0;
  for (const num of mentionedNumbers) {
    if (num < 1) continue;
    const close = realValues.some(v => v > 0 && Math.abs(num - v) / v < 0.20);
    if (close) accurateHits++;
  }
  const accuracy = Math.min(accurateHits / Math.max(mentionedNumbers.length * 0.3, 2), 1);

  // Depth: covers multiple analytical dimensions
  const depthKeywords = [
    ["stake", "concentration", "gini", "distribution"],
    ["validator", "miner", "incentive", "emission"],
    ["trust", "rank", "weight"],
    ["active", "inactive", "participation"],
    ["anomal", "outlier", "pattern", "notable"],
  ];
  const depthScore = depthKeywords.filter(group =>
    group.some(kw => response.toLowerCase().includes(kw))
  ).length / depthKeywords.length;

  const composite = (specificity * 0.35) + (accuracy * 0.35) + (depthScore * 0.30);

  // suppress unused variable warning
  void totalStake;

  return {
    specificity: Math.round(specificity * 10000) / 10000,
    accuracy: Math.round(accuracy * 10000) / 10000,
    depth: Math.round(depthScore * 10000) / 10000,
    composite: Math.round(composite * 10000) / 10000,
  };
}
