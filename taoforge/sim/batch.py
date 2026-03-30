"""Batch runner — queue multiple agent sim runs sequentially.

Runs N agents with varied configs, collects results, and produces
a combined report. Designed for overnight/multi-day experiments.

Usage:
    taoforge batch --agents 10 --cycles 20 --local Qwen/Qwen2.5-1.5B-Instruct
    taoforge batch --agents 50 --cycles 30 --sweep   # auto-vary mutation weights
"""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from taoforge.agent.base import Agent, AgentConfig
from taoforge.evaluation.results import EvalResult
from taoforge.sim.reporter import SimReporter, SimSummary
from taoforge.sim.runner import SimConfig, SimulationRunner

logger = logging.getLogger(__name__)


@dataclass
class AgentRun:
    """Configuration and result for a single agent run."""

    run_id: int
    agent_config: AgentConfig
    sim_config: SimConfig
    label: str = ""
    summary: Optional[SimSummary] = None
    error: Optional[str] = None
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def elapsed_s(self) -> float:
        if self.finished_at and self.started_at:
            return self.finished_at - self.started_at
        return 0.0

    @property
    def improved(self) -> bool:
        return self.summary is not None and self.summary.total_improvement > 0


@dataclass
class BatchConfig:
    """Configuration for a batch of sim runs."""

    num_agents: int = 10
    base_agent_config: Optional[AgentConfig] = None
    base_sim_config: Optional[SimConfig] = None

    # Sweep mode: auto-vary mutation weights and prompts across runs
    sweep: bool = False

    # Optional open-ended evaluator — passed to each SimulationRunner
    evaluator: Optional[Callable[["Agent"], "EvalResult"]] = None

    # Output
    results_dir: str = "batch_results"
    json_output: bool = False
    use_tui: bool = False

    # Auto-push results to GitHub → Vercel after batch completes
    github_token: str = ""
    github_repo: str = "taoforge/taoforge-web"
    github_branch: str = "main"


@dataclass
class BatchSummary:
    """Summary of a full batch run."""

    total_runs: int = 0
    completed: int = 0
    failed: int = 0
    improved: int = 0
    best_improvement: float = 0.0
    best_run_id: int = -1
    avg_improvement: float = 0.0
    avg_final_score: float = 0.0
    avg_cycles: float = 0.0
    total_elapsed_s: float = 0.0
    mutation_stats: dict = field(default_factory=dict)
    runs: list[AgentRun] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "completed": self.completed,
            "failed": self.failed,
            "improved": self.improved,
            "best_improvement": round(self.best_improvement, 4),
            "best_run_id": self.best_run_id,
            "avg_improvement": round(self.avg_improvement, 4),
            "avg_final_score": round(self.avg_final_score, 4),
            "avg_cycles": round(self.avg_cycles, 1),
            "total_elapsed_s": round(self.total_elapsed_s, 1),
            "mutation_stats": self.mutation_stats,
            "runs": [
                {
                    "run_id": r.run_id,
                    "label": r.label,
                    "improved": r.improved,
                    "improvement": round(r.summary.total_improvement, 4) if r.summary else 0,
                    "final_score": round(r.summary.final_score, 4) if r.summary else 0,
                    "cycles": r.summary.total_cycles if r.summary else 0,
                    "accepted": r.summary.accepted_count if r.summary else 0,
                    "elapsed_s": round(r.elapsed_s, 1),
                    "error": r.error,
                }
                for r in self.runs
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Ancient explorers, philosophers, and polymaths
_AGENT_NAMES = [
    # Explorers & navigators
    "Pytheas", "Hanno", "Nearchus", "Scylax", "Eudoxus", "Hippalus",
    "Pythagoras", "Hecataeus", "Megasthenes", "Patrocles",
    # Philosophers & thinkers
    "Thales", "Anaximander", "Heraclitus", "Democritus", "Empedocles",
    "Xenophanes", "Parmenides", "Zeno", "Anaxagoras", "Leucippus",
    # Polymaths & scientists
    "Archimedes", "Eratosthenes", "Hipparchus", "Ptolemy", "Strabo",
    "Posidonius", "Aristarchus", "Ctesibius", "Philo", "Hero",
    # Legendary voyagers
    "Odysseus", "Orpheus", "Daedalus", "Heracles", "Jason",
    "Theseus", "Perseus", "Bellerophon", "Atalanta", "Medea",
]


def _assign_name(index: int, used: set[str]) -> str:
    """Assign a unique name from the pool, cycling if needed."""
    pool = _AGENT_NAMES[:]
    # Start at the index position so different batches get different names
    candidate = pool[index % len(pool)]
    if candidate not in used:
        return candidate
    # Walk forward until we find an unused name
    for offset in range(1, len(pool)):
        candidate = pool[(index + offset) % len(pool)]
        if candidate not in used:
            return candidate
    # Fallback: append index
    return f"{pool[index % len(pool)]}_{index}"


# Sweep variations for mutation weights
_SWEEP_PROFILES = [
    {"label": "baseline", "weights": {"prompt_chain_refactor": 0.35, "inference_pipeline": 0.30, "tool_graph_rewire": 0.15, "lora_merge": 0.15, "memory_index_rebuild": 0.05}},
    {"label": "prompt_heavy", "weights": {"prompt_chain_refactor": 0.60, "inference_pipeline": 0.20, "tool_graph_rewire": 0.10, "lora_merge": 0.05, "memory_index_rebuild": 0.05}},
    {"label": "inference_heavy", "weights": {"prompt_chain_refactor": 0.20, "inference_pipeline": 0.55, "tool_graph_rewire": 0.10, "lora_merge": 0.10, "memory_index_rebuild": 0.05}},
    {"label": "tool_heavy", "weights": {"prompt_chain_refactor": 0.20, "inference_pipeline": 0.20, "tool_graph_rewire": 0.45, "lora_merge": 0.10, "memory_index_rebuild": 0.05}},
    {"label": "balanced", "weights": {"prompt_chain_refactor": 0.25, "inference_pipeline": 0.25, "tool_graph_rewire": 0.20, "lora_merge": 0.20, "memory_index_rebuild": 0.10}},
    {"label": "exploration", "weights": {"prompt_chain_refactor": 0.20, "inference_pipeline": 0.20, "tool_graph_rewire": 0.20, "lora_merge": 0.20, "memory_index_rebuild": 0.20}},
]

_SWEEP_PROMPTS = [
    "You are a helpful assistant.",
    "You are a precise and thorough assistant. Think step by step before answering.",
    "You are an expert problem solver. Break complex problems into parts.",
    "You are a clear communicator. Be concise but complete in your answers.",
    "You are a systematic thinker. Organize your reasoning logically.",
    "You are a rigorous scientist. Support claims with evidence and reasoning.",
    "You are a pragmatic engineer. Focus on working solutions.",
    "You are a careful analyst. Consider edge cases and multiple perspectives.",
]


class BatchRunner:
    """Runs multiple sequential sim runs and collects results."""

    def __init__(self, config: BatchConfig, dashboard=None) -> None:
        self.config = config
        self.dashboard = dashboard  # Optional[DashboardState]
        self._runs: list[AgentRun] = []

    def run(self) -> BatchSummary:
        """Execute all agent runs sequentially."""
        results_dir = Path(self.config.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        agent_runs = self._build_runs()
        total = len(agent_runs)
        batch_start = time.monotonic()

        logger.info(f"Batch starting | {total} agent runs | results -> {results_dir}")
        _print_batch_header(total, self.config)

        if self.dashboard:
            self.dashboard.push_event(
                "batch_start",
                agent="system",
                total_agents=total,
                sweep=self.config.sweep,
            )

        for i, agent_run in enumerate(agent_runs):
            agent_run.started_at = time.monotonic()

            _print_run_start(i + 1, total, agent_run)

            try:
                sim_config = agent_run.sim_config
                sim_config.agent_config = agent_run.agent_config

                # Build reporter — inject dashboard for live streaming
                from taoforge.sim.reporter import SimReporter
                reporter = SimReporter(
                    dashboard=self.dashboard,
                    agent_label=agent_run.label,
                )
                if self.config.use_tui:
                    try:
                        from taoforge.sim.tui import TuiReporter
                        reporter = TuiReporter(json_mode=False)
                    except ImportError:
                        pass

                runner = SimulationRunner(
                    sim_config,
                    reporter=reporter,
                    evaluator=self.config.evaluator,
                )
                summary = runner.run()
                agent_run.summary = summary
                agent_run.finished_at = time.monotonic()

                _print_run_result(i + 1, total, agent_run)

                # Save individual run result
                run_file = results_dir / f"run_{agent_run.run_id:03d}.json"
                run_file.write_text(json.dumps({
                    "run_id": agent_run.run_id,
                    "label": agent_run.label,
                    "elapsed_s": round(agent_run.elapsed_s, 1),
                    "summary": summary.to_dict(),
                }, indent=2))

            except Exception as e:
                agent_run.error = str(e)
                agent_run.finished_at = time.monotonic()
                logger.error(f"Run {agent_run.run_id} failed: {e}")
                _print_run_error(i + 1, total, agent_run)

            self._runs.append(agent_run)

        batch_elapsed = time.monotonic() - batch_start

        # Build batch summary
        summary = self._build_summary(batch_elapsed)

        # Save batch summary
        summary_file = results_dir / "batch_summary.json"
        summary_file.write_text(summary.to_json())

        _print_batch_summary(summary)

        # Auto-push results to GitHub → Vercel if token is set
        token = self.config.github_token or os.environ.get("GITHUB_TOKEN", "")
        if token:
            _push_results_to_github(
                results_dir=results_dir,
                token=token,
                repo=self.config.github_repo,
                branch=self.config.github_branch,
            )

        return summary

    def _build_runs(self) -> list[AgentRun]:
        """Build the list of agent runs to execute."""
        runs = []
        base_agent = self.config.base_agent_config or AgentConfig(
            runtime="local_llm",
            model_name_or_path="Qwen/Qwen2.5-1.5B-Instruct",
            device="cuda",
        )
        base_sim = self.config.base_sim_config or SimConfig(
            max_cycles=20,
            plateau_patience=5,
            json_output=False,
            verbose=False,
        )

        used_names: set[str] = set()
        for i in range(self.config.num_agents):
            agent_config = copy.deepcopy(base_agent)
            sim_config = copy.deepcopy(base_sim)

            name = _assign_name(i, used_names)
            used_names.add(name)
            label = name

            if self.config.sweep:
                # Cycle through sweep profiles
                profile = _SWEEP_PROFILES[i % len(_SWEEP_PROFILES)]
                sim_config.mutation_weights = profile["weights"]

                # Vary initial system prompt
                agent_config.system_prompt = _SWEEP_PROMPTS[i % len(_SWEEP_PROMPTS)]

                # Add some randomness to scoring weights
                if i > 0:
                    sim_config.scoring_weights.w_novelty += random.uniform(-0.05, 0.05)
                    sim_config.scoring_weights.w_breadth += random.uniform(-0.05, 0.05)

            runs.append(AgentRun(
                run_id=i,
                agent_config=agent_config,
                sim_config=sim_config,
                label=label,
            ))

        return runs

    def _build_summary(self, elapsed: float) -> BatchSummary:
        """Build the batch summary from completed runs."""
        completed = [r for r in self._runs if r.summary is not None]
        failed = [r for r in self._runs if r.error is not None]
        improved = [r for r in completed if r.improved]

        # Aggregate mutation stats across all runs
        mutation_stats: dict[str, dict] = {}
        for r in completed:
            if r.summary:
                for mt, stats in r.summary.mutation_stats.items():
                    if mt not in mutation_stats:
                        mutation_stats[mt] = {"attempted": 0, "accepted": 0, "total_improvement": 0.0}
                    mutation_stats[mt]["attempted"] += stats["attempted"]
                    mutation_stats[mt]["accepted"] += stats["accepted"]
                    mutation_stats[mt]["total_improvement"] += stats["total_improvement"]

        best_run = max(completed, key=lambda r: r.summary.total_improvement, default=None)

        return BatchSummary(
            total_runs=len(self._runs),
            completed=len(completed),
            failed=len(failed),
            improved=len(improved),
            best_improvement=best_run.summary.total_improvement if best_run and best_run.summary else 0.0,
            best_run_id=best_run.run_id if best_run else -1,
            avg_improvement=sum(r.summary.total_improvement for r in completed if r.summary) / len(completed) if completed else 0.0,
            avg_final_score=sum(r.summary.final_score for r in completed if r.summary) / len(completed) if completed else 0.0,
            avg_cycles=sum(r.summary.total_cycles for r in completed if r.summary) / len(completed) if completed else 0.0,
            total_elapsed_s=elapsed,
            mutation_stats=mutation_stats,
            runs=self._runs,
        )


# --- Terminal output helpers ---

def _print_batch_header(total: int, config: BatchConfig) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console(stderr=True)
        mode = "sweep" if config.sweep else "uniform"
        console.print(Panel(
            f"[bold]Agents:[/bold] {total}  |  [bold]Mode:[/bold] {mode}  |  "
            f"[bold]Results:[/bold] {config.results_dir}/",
            title="[bold cyan]TaoForge Batch Runner[/bold cyan]",
            border_style="cyan",
        ))
    except ImportError:
        import sys
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  TaoForge Batch Runner | {total} agents", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)


def _print_run_start(current: int, total: int, run: AgentRun) -> None:
    try:
        from rich.console import Console
        console = Console(stderr=True)
        console.print(f"\n[bold cyan][{current}/{total}][/bold cyan] Starting [bold]{run.label}[/bold]")
    except ImportError:
        import sys
        print(f"\n[{current}/{total}] Starting {run.label}", file=sys.stderr)


def _print_run_result(current: int, total: int, run: AgentRun) -> None:
    try:
        from rich.console import Console
        console = Console(stderr=True)
        s = run.summary
        if s and s.total_improvement > 0:
            console.print(
                f"[bold cyan][{current}/{total}][/bold cyan] [bold green]IMPROVED[/bold green] "
                f"{run.label}: {s.initial_score:.4f} -> {s.final_score:.4f} "
                f"([green]+{s.total_improvement:.4f}[/green]) | "
                f"{s.accepted_count}/{s.total_cycles} accepted | {run.elapsed_s:.0f}s"
            )
        else:
            console.print(
                f"[bold cyan][{current}/{total}][/bold cyan] [dim]NO CHANGE[/dim] "
                f"{run.label}: {s.final_score:.4f} | "
                f"{s.accepted_count}/{s.total_cycles} accepted | {run.elapsed_s:.0f}s"
                if s else f"[bold cyan][{current}/{total}][/bold cyan] [dim]NO RESULT[/dim] {run.label}"
            )
    except ImportError:
        import sys
        s = run.summary
        if s:
            print(f"[{current}/{total}] {run.label}: {s.initial_score:.4f} -> {s.final_score:.4f} ({s.total_improvement:+.4f}) | {run.elapsed_s:.0f}s", file=sys.stderr)


def _print_run_error(current: int, total: int, run: AgentRun) -> None:
    try:
        from rich.console import Console
        console = Console(stderr=True)
        console.print(f"[bold cyan][{current}/{total}][/bold cyan] [bold red]FAILED[/bold red] {run.label}: {run.error}")
    except ImportError:
        import sys
        print(f"[{current}/{total}] FAILED {run.label}: {run.error}", file=sys.stderr)


def _print_batch_summary(summary: BatchSummary) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        console = Console(stderr=True)

        console.print()
        console.rule("[bold]Batch Complete[/bold]")

        table = Table(show_header=False, padding=(0, 2), expand=True)
        table.add_column("key", style="dim")
        table.add_column("val", style="bold")
        table.add_row("Runs", f"{summary.completed} completed, {summary.failed} failed")
        table.add_row("Improved", f"{summary.improved}/{summary.completed} ({summary.improved/summary.completed*100:.0f}%)" if summary.completed else "0")
        table.add_row("Best improvement", f"+{summary.best_improvement:.4f} (run {summary.best_run_id})")
        table.add_row("Avg improvement", f"+{summary.avg_improvement:.4f}")
        table.add_row("Avg final score", f"{summary.avg_final_score:.4f}")
        table.add_row("Avg cycles", f"{summary.avg_cycles:.1f}")
        table.add_row("Total time", f"{summary.total_elapsed_s/60:.1f} minutes")
        console.print(table)

        if summary.mutation_stats:
            console.print()
            mt_table = Table(title="Mutation Stats (All Runs)", expand=True)
            mt_table.add_column("Mutation", style="cyan")
            mt_table.add_column("Accepted", justify="right")
            mt_table.add_column("Attempted", justify="right")
            mt_table.add_column("Rate", justify="right")
            mt_table.add_column("Total Improvement", justify="right")

            for mt, stats in sorted(summary.mutation_stats.items()):
                rate = stats["accepted"] / stats["attempted"] * 100 if stats["attempted"] > 0 else 0
                mt_table.add_row(
                    mt, str(stats["accepted"]), str(stats["attempted"]),
                    f"{rate:.0f}%", f"+{stats['total_improvement']:.4f}",
                )
            console.print(mt_table)

        # Leaderboard
        improved_runs = sorted(
            [r for r in summary.runs if r.improved],
            key=lambda r: r.summary.total_improvement if r.summary else 0,
            reverse=True,
        )
        if improved_runs:
            console.print()
            lb = Table(title="Leaderboard (Top Runs)", expand=True)
            lb.add_column("Rank", width=5, justify="right")
            lb.add_column("Run", style="cyan")
            lb.add_column("Label")
            lb.add_column("Score", justify="right")
            lb.add_column("Improvement", justify="right", style="green")
            lb.add_column("Cycles", justify="right")

            for rank, r in enumerate(improved_runs[:10], 1):
                s = r.summary
                lb.add_row(
                    str(rank), str(r.run_id), r.label,
                    f"{s.final_score:.4f}" if s else "-",
                    f"+{s.total_improvement:.4f}" if s else "-",
                    str(s.total_cycles) if s else "-",
                )
            console.print(lb)

    except ImportError:
        import sys
        print(f"\nBatch Complete: {summary.completed} runs, {summary.improved} improved", file=sys.stderr)
        print(f"Best: +{summary.best_improvement:.4f} (run {summary.best_run_id})", file=sys.stderr)
        print(f"Avg improvement: +{summary.avg_improvement:.4f}", file=sys.stderr)
        print(f"Total time: {summary.total_elapsed_s/60:.1f} minutes", file=sys.stderr)


def _push_results_to_github(results_dir: Path, token: str, repo: str, branch: str) -> None:
    """Transform batch results and push to GitHub → triggers Vercel deploy."""
    try:
        # Import transformer (works whether run from repo root or installed)
        import sys
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))

        from push_results import build_frontend_json, push_to_github

        try:
            from rich.console import Console
            console = Console(stderr=True)
            console.print("\n[bold cyan]📡 Pushing results to GitHub → Vercel...[/bold cyan]")
        except ImportError:
            print("\n📡 Pushing results to GitHub → Vercel...", file=sys.stderr)

        frontend_json = build_frontend_json(results_dir)
        url = push_to_github(
            content=frontend_json,
            token=token,
            repo=repo,
            branch=branch,
            path="public/data/batch-results.json",
        )

        try:
            console.print(f"[bold green]✅ Dashboard updated![/bold green] Deploying to Vercel now...")
            console.print(f"[dim]   File: {url}[/dim]")
            console.print(f"[bold]🌐 Live in ~30s → https://taoforge-web.vercel.app[/bold]")
        except Exception:
            print(f"✅ Dashboard updated: {url}", file=sys.stderr)
            print(f"🌐 Live in ~30s → https://taoforge-web.vercel.app", file=sys.stderr)

    except Exception as e:
        logger.warning(f"Failed to push results to GitHub: {e}")
