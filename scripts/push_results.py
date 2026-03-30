#!/usr/bin/env python3
"""
push_results.py — Transform batch results and push to GitHub → auto-deploys to Vercel.

Usage:
    python scripts/push_results.py --batch-dir /workspace/batch_results

Environment variables:
    GITHUB_TOKEN   — PAT with repo write access (required)
    GITHUB_REPO    — e.g. "taoforge/taoforge-web" (default: taoforge/taoforge-web)
    GITHUB_BRANCH  — branch to push to (default: main)
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path


# ──────────────────────────────────────────────────────────────────────────────
# Mutation name mapping
# ──────────────────────────────────────────────────────────────────────────────

MUTATION_LABELS = {
    "prompt_chain_refactor": "Prompt Chain Refactor",
    "inference_pipeline":    "Inference Pipeline",
    "lora_merge":            "LoRA Merge",
    "tool_graph_rewire":     "Tool Graph Rewire",
    "memory_index_rebuild":  "Memory Index Rebuild",
}


# ──────────────────────────────────────────────────────────────────────────────
# Transform batch results → frontend JSON
# ──────────────────────────────────────────────────────────────────────────────

def compute_streak(cycles: list) -> int:
    """Count consecutive accepted cycles from the end of the run."""
    streak = 0
    for c in reversed(cycles):
        if c.get("accepted"):
            streak += 1
        else:
            break
    return streak


def build_frontend_json(batch_dir: Path) -> dict:
    summary_path = batch_dir / "batch_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"batch_summary.json not found in {batch_dir}")

    with open(summary_path) as f:
        summary = json.load(f)

    # Load all individual run files
    runs_data = []
    for run_meta in summary["runs"]:
        run_id = run_meta["run_id"]
        run_path = batch_dir / f"run_{run_id:03d}.json"
        if run_path.exists():
            with open(run_path) as f:
                runs_data.append(json.load(f))

    # ── Stats ─────────────────────────────────────────────────────────────────
    total_cycles = sum(r["summary"]["total_cycles"] for r in runs_data)
    total_accepted = sum(r["summary"]["accepted"] for r in runs_data)

    stats = {
        "active_agents":        summary["total_runs"],
        "total_cycles":         total_cycles,
        "verified_improvements": total_accepted,
        "avg_delta":            round(summary["avg_improvement"], 4),
    }

    # ── Leaderboard (sorted by final score desc) ───────────────────────────────
    leaderboard = []
    for r in runs_data:
        s = r["summary"]
        cycles = s.get("cycles", [])
        leaderboard.append({
            "name":         r["label"],
            "score":        round(s["final_score"], 4),
            "improvements": s["accepted"],
            "streak":       compute_streak(cycles),
            "initial":      round(s["initial_score"], 4),
            "delta":        round(s["total_improvement"], 4),
        })
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    # ── Events (all cycles across all runs) ────────────────────────────────────
    events = []
    event_id = 1
    for r in runs_data:
        s = r["summary"]
        for c in s.get("cycles", []):
            mut_key  = c.get("mutation_type", "")
            mut_name = MUTATION_LABELS.get(mut_key, mut_key)
            accepted = c.get("accepted", False)
            events.append({
                "id":              event_id,
                "type":            "improvement" if accepted else "mutation",
                "agent":           r["label"],
                "mutation":        mut_name,
                "score":           round(c.get("delta_score", 0), 4),
                "delta":           round(c.get("raw_improvement", 0), 4),
                "cycle":           c.get("cycle", event_id),
                "accepted":        accepted,
                "baseline_score":  round(c.get("baseline_score", 0), 4),
                "composite_score": round(c.get("composite_score", 0), 4),
                "holdout_score":   round(c.get("holdout_score", 0), 4),
                "regressions":     c.get("regressions", []),
            })
            event_id += 1

    # ── Mutation aggregate stats ───────────────────────────────────────────────
    mut_agg = summary.get("mutation_stats", {})
    mutations = []
    for key, label in MUTATION_LABELS.items():
        m = mut_agg.get(key, {})
        attempted = m.get("attempted", 0)
        accepted_  = m.get("accepted", 0)
        mutations.append({
            "name":              label,
            "attempted":         attempted,
            "accepted":          accepted_,
            "rate":              round(accepted_ / attempted * 100, 1) if attempted else 0.0,
            "total_improvement": round(m.get("total_improvement", 0), 4),
        })
    mutations.sort(key=lambda x: x["rate"], reverse=True)

    # ── Runs (ordered by run_id) ───────────────────────────────────────────────
    runs_out = []
    for r in runs_data:
        s = r["summary"]
        runs_out.append({
            "label":             r["label"],
            "initial_score":     round(s["initial_score"], 4),
            "final_score":       round(s["final_score"], 4),
            "total_improvement": round(s["total_improvement"], 4),
            "accepted":          s["accepted"],
            "total_cycles":      s["total_cycles"],
            "dag_depth":         s.get("dag_depth", 0),
            "reputation":        round(s.get("reputation", 0), 4),
            "elapsed_s":         round(r.get("elapsed_s", 0), 1),
        })

    return {
        "stats":      stats,
        "leaderboard": leaderboard,
        "events":     events,
        "mutations":  mutations,
        "runs":       runs_out,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GitHub API push
# ──────────────────────────────────────────────────────────────────────────────

def push_to_github(content: dict, token: str, repo: str, branch: str, path: str):
    import urllib.request
    import urllib.error

    api_base = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
    }

    # Get current SHA (needed for update)
    sha = None
    try:
        req = urllib.request.Request(f"{api_base}?ref={branch}", headers=headers)
        with urllib.request.urlopen(req) as resp:
            existing = json.loads(resp.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    # Encode content
    content_b64 = base64.b64encode(
        json.dumps(content, indent=2).encode()
    ).decode()

    payload = {
        "message": f"chore: update batch results ({content['stats']['active_agents']} agents, "
                   f"avg score {content['stats']['avg_delta']:.3f})",
        "content": content_b64,
        "branch":  branch,
    }
    if sha:
        payload["sha"] = sha

    data = json.dumps(payload).encode()
    req = urllib.request.Request(api_base, data=data, headers=headers, method="PUT")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result["content"]["html_url"]


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Push batch results to GitHub → Vercel")
    parser.add_argument("--batch-dir", required=True,
                        help="Path to batch results directory (contains batch_summary.json)")
    parser.add_argument("--repo",   default=os.environ.get("GITHUB_REPO", "taoforge/taoforge-web"),
                        help="GitHub repo (default: taoforge/taoforge-web)")
    parser.add_argument("--branch", default=os.environ.get("GITHUB_BRANCH", "main"),
                        help="Branch to push to (default: main)")
    parser.add_argument("--file",   default="public/data/batch-results.json",
                        help="Path in repo to update")
    parser.add_argument("--dry-run", action="store_true",
                        help="Transform but don't push — print JSON instead")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    print(f"📂  Loading results from {batch_dir}...")
    frontend_json = build_frontend_json(batch_dir)

    n_agents  = frontend_json["stats"]["active_agents"]
    n_cycles  = frontend_json["stats"]["total_cycles"]
    n_improved = sum(1 for r in frontend_json["runs"] if r["total_improvement"] > 0)
    avg_score = sum(r["final_score"] for r in frontend_json["runs"]) / max(n_agents, 1)

    print(f"✅  Transformed: {n_agents} agents, {n_cycles} cycles, "
          f"{n_improved}/{n_agents} improved, avg final score {avg_score:.4f}")

    if args.dry_run:
        print(json.dumps(frontend_json, indent=2))
        return

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌  GITHUB_TOKEN not set. Export it or use --dry-run.", file=sys.stderr)
        sys.exit(1)

    print(f"🚀  Pushing to {args.repo}/{args.file} @ {args.branch}...")
    url = push_to_github(frontend_json, token, args.repo, args.branch, args.file)
    print(f"✅  Pushed! File URL: {url}")
    print(f"🌐  Vercel will deploy in ~30s → https://taoforge-web.vercel.app")


if __name__ == "__main__":
    main()
