#!/usr/bin/env python3
"""
push_results.py — Transform batch results and push to GitHub → auto-deploys to Vercel.

Merges new batch into existing batch-results.json so the dashboard accumulates
agents across multiple runs rather than replacing them.

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
    "subnet_switch":         "Subnet Switch",
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
        "active_agents":         summary["total_runs"],
        "total_cycles":          total_cycles,
        "verified_improvements": total_accepted,
        "avg_delta":             round(summary["avg_improvement"], 4),
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
                "thought":         c.get("thought", ""),
            })
            event_id += 1

    # ── Mutation aggregate stats ───────────────────────────────────────────────
    mut_agg = summary.get("mutation_stats", {})
    mutations = []
    for key, label in MUTATION_LABELS.items():
        m = mut_agg.get(key, {})
        attempted = m.get("attempted", 0)
        accepted_ = m.get("accepted", 0)
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
            "thought_log":       s.get("thought_log", []),
            "self_portrait_svg": s.get("self_portrait_svg", ""),
            "netuid":            s.get("netuid", 1),
            "subnet_history":    s.get("subnet_history", []),
        })

    return {
        "stats":      stats,
        "leaderboard": leaderboard,
        "events":     events,
        "mutations":  mutations,
        "runs":       runs_out,
    }


def merge_results(existing: dict, new: dict) -> dict:
    """Merge a new batch into existing accumulated results.

    - Runs: add new agents; if name collides, keep the higher-scoring one
    - Events: append new events, re-numbering IDs sequentially
    - Mutations: aggregate counts across all batches
    - Stats: recompute from merged runs + events
    """
    # ── Runs: merge by name, keep higher final_score on collision ──────────────
    existing_runs = {r["label"]: r for r in existing.get("runs", [])}
    for run in new.get("runs", []):
        name = run["label"]
        if name not in existing_runs:
            existing_runs[name] = run
        else:
            # Keep whichever run has the higher final score
            if run["final_score"] > existing_runs[name]["final_score"]:
                # Preserve subnet_history from the winning run
                existing_runs[name] = run

    merged_runs = list(existing_runs.values())
    merged_runs.sort(key=lambda r: r["final_score"], reverse=True)

    # ── Events: append new, re-number IDs ─────────────────────────────────────
    existing_events = existing.get("events", [])
    new_events = new.get("events", [])

    # Find the set of (agent, cycle) pairs already in existing to avoid dupes
    existing_keys = {(e["agent"], e.get("cycle"), e.get("mutation")) for e in existing_events}
    to_add = [
        e for e in new_events
        if (e["agent"], e.get("cycle"), e.get("mutation")) not in existing_keys
    ]

    merged_events = existing_events + to_add
    # Re-number IDs sequentially
    for i, e in enumerate(merged_events, 1):
        e["id"] = i

    # ── Mutations: aggregate counts ────────────────────────────────────────────
    mut_index = {m["name"]: m for m in existing.get("mutations", [])}
    for m in new.get("mutations", []):
        if m["name"] in mut_index:
            ex = mut_index[m["name"]]
            ex["attempted"]         += m["attempted"]
            ex["accepted"]          += m["accepted"]
            ex["total_improvement"] = round(ex["total_improvement"] + m["total_improvement"], 4)
            ex["rate"] = round(
                ex["accepted"] / ex["attempted"] * 100, 1
            ) if ex["attempted"] else 0.0
        else:
            mut_index[m["name"]] = dict(m)

    merged_mutations = sorted(mut_index.values(), key=lambda m: m["rate"], reverse=True)

    # ── Stats: recompute from merged data ──────────────────────────────────────
    total_cycles     = sum(r["total_cycles"] for r in merged_runs)
    total_accepted   = sum(r["accepted"] for r in merged_runs)
    improved_runs    = [r for r in merged_runs if r["total_improvement"] > 0]
    avg_delta        = (
        sum(r["total_improvement"] for r in improved_runs) / len(improved_runs)
        if improved_runs else 0.0
    )

    merged_stats = {
        "active_agents":         len(merged_runs),
        "total_cycles":          total_cycles,
        "verified_improvements": total_accepted,
        "avg_delta":             round(avg_delta, 4),
    }

    # ── Leaderboard: rebuild from merged runs ──────────────────────────────────
    merged_leaderboard = [
        {
            "name":         r["label"],
            "score":        r["final_score"],
            "improvements": r["accepted"],
            "streak":       compute_streak(r.get("thought_log", [])),
            "initial":      r["initial_score"],
            "delta":        r["total_improvement"],
        }
        for r in merged_runs
    ]
    merged_leaderboard.sort(key=lambda x: x["score"], reverse=True)

    return {
        "stats":       merged_stats,
        "leaderboard": merged_leaderboard,
        "events":      merged_events,
        "mutations":   merged_mutations,
        "runs":        merged_runs,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GitHub API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_existing_from_github(token: str, repo: str, branch: str, path: str) -> dict | None:
    """Fetch the current batch-results.json from GitHub, return parsed dict or None."""
    import urllib.request
    import urllib.error

    api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
    }
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            content = base64.b64decode(data["content"]).decode()
            return json.loads(content)
    except Exception:
        return None


def push_to_github(content: dict, token: str, repo: str, branch: str, path: str):
    import urllib.request

    api_base = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
    }

    # Get current SHA (needed for update)
    sha = None
    try:
        import urllib.error
        req = urllib.request.Request(f"{api_base}?ref={branch}", headers=headers)
        with urllib.request.urlopen(req) as resp:
            existing = json.loads(resp.read())
            sha = existing.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    content_b64 = base64.b64encode(
        json.dumps(content, indent=2).encode()
    ).decode()

    n = content["stats"]["active_agents"]
    avg = content["stats"]["avg_delta"]
    payload = {
        "message": f"chore: update batch results ({n} agents, avg delta {avg:.3f})",
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
    parser.add_argument("--repo",    default=os.environ.get("GITHUB_REPO", "taoforge/taoforge-web"),
                        help="GitHub repo (default: taoforge/taoforge-web)")
    parser.add_argument("--branch",  default=os.environ.get("GITHUB_BRANCH", "main"),
                        help="Branch to push to (default: main)")
    parser.add_argument("--file",    default="public/data/batch-results.json",
                        help="Path in repo to update")
    parser.add_argument("--no-merge", action="store_true",
                        help="Replace instead of merging with existing results")
    parser.add_argument("--dry-run", action="store_true",
                        help="Transform but don't push — print JSON instead")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    print(f"📂  Loading results from {batch_dir}...")
    new_json = build_frontend_json(batch_dir)

    token = os.environ.get("GITHUB_TOKEN")

    # Merge with existing unless --no-merge
    if not args.no_merge and not args.dry_run:
        if not token:
            print("⚠️  GITHUB_TOKEN not set — skipping merge, will replace existing results.")
            frontend_json = new_json
        else:
            print(f"🔄  Fetching existing results from GitHub to merge...")
            existing = fetch_existing_from_github(token, args.repo, args.branch, args.file)
            if existing:
                prev_agents = existing["stats"]["active_agents"]
                frontend_json = merge_results(existing, new_json)
                print(f"✅  Merged: {prev_agents} existing + {new_json['stats']['active_agents']} new "
                      f"= {frontend_json['stats']['active_agents']} total agents")
            else:
                print("ℹ️  No existing results found — pushing fresh.")
                frontend_json = new_json
    else:
        frontend_json = new_json

    n_agents   = frontend_json["stats"]["active_agents"]
    n_cycles   = frontend_json["stats"]["total_cycles"]
    n_improved = sum(1 for r in frontend_json["runs"] if r["total_improvement"] > 0)
    avg_score  = sum(r["final_score"] for r in frontend_json["runs"]) / max(n_agents, 1)

    print(f"📊  Results: {n_agents} agents, {n_cycles} cycles, "
          f"{n_improved}/{n_agents} improved, avg final score {avg_score:.4f}")

    if args.dry_run:
        print(json.dumps(frontend_json, indent=2))
        return

    if not token:
        print("❌  GITHUB_TOKEN not set. Export it or use --dry-run.", file=sys.stderr)
        sys.exit(1)

    print(f"🚀  Pushing to {args.repo}/{args.file} @ {args.branch}...")
    url = push_to_github(frontend_json, token, args.repo, args.branch, args.file)
    print(f"✅  Pushed! {url}")
    print(f"🌐  Vercel will deploy in ~30s → https://taoforge-web.vercel.app")


if __name__ == "__main__":
    main()
