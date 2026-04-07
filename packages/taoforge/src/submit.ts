import { RunResult } from "./types.js";

const DEFAULT_API = "https://spellingly-mealiest-ignacia.ngrok-free.app";

export async function submitResults(
  result: RunResult,
  apiUrl: string = DEFAULT_API,
): Promise<{ ok: boolean; url?: string; error?: string }> {
  try {
    const res = await fetch(`${apiUrl}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_name: result.agent_name,
        model: result.model,
        netuid: result.netuid,
        initial_score: result.initial_score,
        final_score: result.final_score,
        total_improvement: result.total_improvement,
        accepted: result.accepted,
        total_cycles: result.total_cycles,
        thought_log: result.thought_log,
        self_portrait_svg: result.self_portrait_svg,
        subnet_history: result.subnet_history,
        source: "external",
      }),
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: `Server returned ${res.status}: ${text}` };
    }
    const data = await res.json() as { ok: boolean; agent: string; score: number };
    void data;
    return { ok: true, url: `${apiUrl.replace(/\/api.*/, "")}/dashboard` };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}
