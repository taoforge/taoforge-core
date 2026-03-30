"""Simulation reporter — terminal dashboard and JSON output."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from taoforge.agent.base import Agent, AgentConfig
from taoforge.evaluation.results import EvalResult, ScoreVector
from taoforge.evaluation.suite import BenchmarkSuite


@dataclass
class CycleResult:
    """Result of a single simulation cycle."""

    cycle_num: int = 0
    mutation_type: str = ""
    mutation_description: str = ""
    baseline_score: float = 0.0
    delta_score: float = 0.0
    raw_improvement: float = 0.0
    composite_score: float = 0.0
    score_vector: Optional[ScoreVector] = None
    accepted: bool = False
    proposal_id: Optional[str] = None
    delta_result: Optional[EvalResult] = None
    holdout_score: float = 0.0
    cycle_time_s: float = 0.0

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        d = {
            "cycle": self.cycle_num,
            "mutation_type": self.mutation_type,
            "mutation_description": self.mutation_description,
            "baseline_score": round(self.baseline_score, 4),
            "delta_score": round(self.delta_score, 4),
            "raw_improvement": round(self.raw_improvement, 4),
            "composite_score": round(self.composite_score, 4),
            "holdout_score": round(self.holdout_score, 4),
            "accepted": self.accepted,
            "proposal_id": self.proposal_id,
            "cycle_time_s": round(self.cycle_time_s, 2),
        }
        if self.score_vector:
            d["breadth"] = round(self.score_vector.breadth, 4)
            d["regressions"] = self.score_vector.regression_flags
        return d


@dataclass
class SimSummary:
    """Summary of a complete simulation run."""

    total_cycles: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    initial_score: float = 0.0
    final_score: float = 0.0
    total_improvement: float = 0.0
    best_composite_score: float = 0.0
    mutation_stats: dict = field(default_factory=dict)
    dag_depth: int = 0
    reputation: float = 0.0
    elapsed_s: float = 0.0
    cycles: list[CycleResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "accepted": self.accepted_count,
            "rejected": self.rejected_count,
            "initial_score": round(self.initial_score, 4),
            "final_score": round(self.final_score, 4),
            "total_improvement": round(self.total_improvement, 4),
            "improvement_pct": round(
                (self.total_improvement / self.initial_score * 100)
                if self.initial_score > 0 else 0.0, 1
            ),
            "best_composite_score": round(self.best_composite_score, 4),
            "mutation_stats": self.mutation_stats,
            "dag_depth": self.dag_depth,
            "reputation": round(self.reputation, 4),
            "elapsed_s": round(self.elapsed_s, 1),
            "cycles": [c.to_dict() for c in self.cycles],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Terminal formatting helpers
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"
_CHECK = "+"
_CROSS = "x"
_ARROW = "->"


class SimReporter:
    """Reports simulation progress to terminal and/or JSON.

    Optionally pushes events to a DashboardState for live web dashboard updates.
    Pass `dashboard` to enable real-time streaming to the frontend.
    """

    def __init__(
        self,
        json_mode: bool = False,
        dashboard=None,   # Optional[DashboardState] — avoid circular import
        agent_label: str = "",
    ) -> None:
        self.json_mode = json_mode
        self.dashboard = dashboard
        self.agent_label = agent_label
        self._json_events: list[dict] = []
        self._agent_id: str = ""
        self._run_num: int = 0

    def print_header(self, config, agent: Agent, suite: BenchmarkSuite) -> None:
        self._agent_id = agent.agent_id
        label = self.agent_label or agent.agent_id[:12]

        if self.json_mode:
            self._json_events.append({
                "event": "sim_start",
                "agent_id": agent.agent_id,
                "agent_runtime": agent.config.runtime,
                "suite_id": suite.suite_id,
                "suite_tasks": suite.size,
                "max_cycles": config.max_cycles,
            })

        if self.dashboard:
            self.dashboard.push_event(
                "agent_start",
                agent=label,
                agent_id=agent.agent_id,
                suite_id=suite.suite_id,
                max_cycles=config.max_cycles,
            )
            self.dashboard.update_stats(
                active_agents=self.dashboard.stats["active_agents"] + 1,
                total_cycles=self.dashboard.stats["total_cycles"],
                verified_improvements=self.dashboard.stats["verified_improvements"],
                avg_delta=self.dashboard.stats["avg_delta"],
            )

        if self.json_mode:
            return

        _p(f"\n{_BOLD}{'=' * 60}{_RESET}")
        _p(f"{_BOLD}  TaoForge Simulation{_RESET}")
        _p(f"{'=' * 60}")
        _p(f"  Agent:      {agent}")
        _p(f"  Suite:      {suite.suite_id} ({suite.size} tasks)")
        _p(f"  Categories: {', '.join(sorted(suite.categories))}")
        _p(f"  Max cycles: {config.max_cycles}")
        _p(f"  Plateau:    stop after {config.plateau_patience} cycles w/o improvement")
        _p(f"{'=' * 60}\n")

    def print_baseline(self, result: EvalResult) -> None:
        label = self.agent_label or self._agent_id[:12]
        task_scores = {t.task_id: round(t.score, 4) for t in result.task_scores}

        if self.json_mode:
            self._json_events.append({
                "event": "baseline",
                "score": round(result.aggregate_score, 4),
                "tasks": task_scores,
            })

        if self.dashboard:
            self.dashboard.push_event(
                "baseline",
                agent=label,
                score=round(result.aggregate_score, 4),
                tasks=task_scores,
            )
            self.dashboard.update_score(
                self._agent_id,
                score=result.aggregate_score,
            )

        if self.json_mode:
            return

        _p(f"  {_BOLD}Baseline:{_RESET} {result.aggregate_score:.4f}")
        for ts in result.task_scores:
            bar = _score_bar(ts.score)
            _p(f"    {ts.task_id:.<30s} {bar} {ts.score:.3f}")
        _p("")

    def print_cycle(self, result: CycleResult) -> None:
        label = self.agent_label or self._agent_id[:12]

        if self.json_mode:
            self._json_events.append({"event": "cycle", **result.to_dict()})

        if self.dashboard:
            event_type = "cycle_accepted" if result.accepted else "cycle_rejected"
            self.dashboard.push_event(
                event_type,
                agent=label,
                cycle=result.cycle_num,
                mutation_type=result.mutation_type,
                baseline_score=round(result.baseline_score, 4),
                delta_score=round(result.delta_score, 4),
                improvement=round(result.raw_improvement, 4),
                composite_score=round(result.composite_score, 4),
                cycle_time_s=round(result.cycle_time_s, 1),
                regressions=result.score_vector.regression_flags if result.score_vector else [],
            )
            self.dashboard.update_score(
                self._agent_id,
                score=result.delta_score if result.accepted else result.baseline_score,
                improvement=result.raw_improvement,
                mutation_type=result.mutation_type if result.accepted else "",
            )
            # Update global stats
            total = self.dashboard.stats["total_cycles"] + 1
            improvements = self.dashboard.stats["verified_improvements"] + (1 if result.accepted else 0)
            all_deltas = [
                e.get("improvement", 0)
                for e in list(self.dashboard.events)
                if e.get("type") == "cycle_accepted"
            ]
            avg = sum(all_deltas) / len(all_deltas) if all_deltas else 0.0
            self.dashboard.update_stats(
                active_agents=self.dashboard.stats["active_agents"],
                total_cycles=total,
                verified_improvements=improvements,
                avg_delta=avg,
            )

        if self.json_mode:
            return

        status = f"{_GREEN}{_CHECK} accepted{_RESET}" if result.accepted else f"{_RED}{_CROSS} rejected{_RESET}"
        delta_str = f"{result.raw_improvement:+.4f}"
        if result.raw_improvement > 0:
            delta_str = f"{_GREEN}{delta_str}{_RESET}"
        elif result.raw_improvement < 0:
            delta_str = f"{_RED}{delta_str}{_RESET}"

        _p(
            f"  [{result.cycle_num:3d}] {result.mutation_type:<25s} "
            f"{result.baseline_score:.4f} {_ARROW} {result.delta_score:.4f} "
            f"({delta_str}) "
            f"score={result.composite_score:.3f} "
            f"{status} "
            f"{_DIM}({result.cycle_time_s:.1f}s){_RESET}"
        )

        if result.score_vector and result.score_vector.regression_flags:
            regs = ", ".join(result.score_vector.regression_flags)
            _p(f"        {_YELLOW}regressions: {regs}{_RESET}")

    def print_plateau(self, cycle: int, patience: int) -> None:
        if self.json_mode:
            self._json_events.append({"event": "plateau", "cycle": cycle, "patience": patience})
            return

        _p(f"\n  {_YELLOW}Plateau detected at cycle {cycle} "
           f"({patience} cycles without improvement). Stopping.{_RESET}\n")

    def print_summary(self, summary: SimSummary) -> None:
        label = self.agent_label or self._agent_id[:12]

        if self.dashboard:
            self.dashboard.push_event(
                "agent_complete",
                agent=label,
                total_cycles=summary.total_cycles,
                accepted=summary.accepted_count,
                rejected=summary.rejected_count,
                initial_score=round(summary.initial_score, 4),
                final_score=round(summary.final_score, 4),
                improvement=round(summary.total_improvement, 4),
                improvement_pct=round(
                    summary.total_improvement / summary.initial_score * 100
                    if summary.initial_score > 0 else 0.0, 1
                ),
                mutation_stats=summary.mutation_stats,
            )
            self.dashboard.update_stats(
                active_agents=max(0, self.dashboard.stats["active_agents"] - 1),
                total_cycles=self.dashboard.stats["total_cycles"],
                verified_improvements=self.dashboard.stats["verified_improvements"],
                avg_delta=self.dashboard.stats["avg_delta"],
            )

        if self.json_mode:
            full = {"event": "summary", **summary.to_dict(), "events": self._json_events}
            print(json.dumps(full, indent=2))
            return

        improvement_pct = (
            summary.total_improvement / summary.initial_score * 100
            if summary.initial_score > 0 else 0.0
        )

        _p(f"\n{'=' * 60}")
        _p(f"{_BOLD}  Simulation Results{_RESET}")
        _p(f"{'=' * 60}")
        _p(f"  Cycles:      {summary.total_cycles} "
           f"({_GREEN}{summary.accepted_count} accepted{_RESET}, "
           f"{_RED}{summary.rejected_count} rejected{_RESET})")
        _p(f"  Score:       {summary.initial_score:.4f} {_ARROW} "
           f"{summary.final_score:.4f} "
           f"({_GREEN}{summary.total_improvement:+.4f}{_RESET}, "
           f"{improvement_pct:+.1f}%)")
        _p(f"  Best score:  {summary.best_composite_score:.4f}")
        _p(f"  DAG depth:   {summary.dag_depth}")
        _p(f"  Reputation:  {summary.reputation:.4f}")
        _p(f"  Time:        {summary.elapsed_s:.1f}s")

        if summary.mutation_stats:
            _p(f"\n  {_BOLD}Mutation Stats:{_RESET}")
            for mt, stats in sorted(summary.mutation_stats.items()):
                rate = stats["accepted"] / stats["attempted"] * 100 if stats["attempted"] > 0 else 0
                _p(f"    {mt:<28s} {stats['accepted']}/{stats['attempted']} accepted "
                   f"({rate:.0f}%) | improvement: {stats['total_improvement']:+.4f}")

        _p(f"{'=' * 60}\n")


def _p(text: str) -> None:
    """Print to stderr (so JSON can go to stdout)."""
    print(text, file=sys.stderr)


def _score_bar(score: float, width: int = 20) -> str:
    """Generate a visual score bar."""
    filled = int(score * width)
    empty = width - filled
    bar = "#" * filled + "." * empty
    if score >= 0.7:
        return f"{_GREEN}[{bar}]{_RESET}"
    elif score >= 0.4:
        return f"{_YELLOW}[{bar}]{_RESET}"
    else:
        return f"{_RED}[{bar}]{_RESET}"
