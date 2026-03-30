"""Live terminal dashboard for TaoForge simulation — powered by rich."""

from __future__ import annotations

import time
from typing import Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from taoforge.agent.base import Agent
from taoforge.evaluation.results import EvalResult
from taoforge.evaluation.suite import BenchmarkSuite
from taoforge.sim.reporter import CycleResult, SimSummary


class TuiReporter:
    """Rich Live dashboard reporter — drop-in replacement for SimReporter.

    Implements the same 5-method interface as SimReporter:
    print_header, print_baseline, print_cycle, print_plateau, print_summary.
    """

    def __init__(self, json_mode: bool = False) -> None:
        self.json_mode = json_mode
        self.console = Console(stderr=True)

        # State
        self._config = None
        self._agent: Optional[Agent] = None
        self._suite: Optional[BenchmarkSuite] = None
        self._baseline_score: float = 0.0
        self._baseline_tasks: list[tuple[str, float]] = []
        self._cycles: list[CycleResult] = []
        self._plateau_msg: str = ""
        self._start_time: float = 0.0

        # Live context
        self._live: Optional[Live] = None

    def print_header(self, config, agent: Agent, suite: BenchmarkSuite) -> None:
        self._config = config
        self._agent = agent
        self._suite = suite
        self._start_time = time.monotonic()

        self._live = Live(
            self._build_layout(),
            console=self.console,
            refresh_per_second=2,
            vertical_overflow="visible",
        )
        self._live.start()

    def print_baseline(self, result: EvalResult) -> None:
        self._baseline_score = result.aggregate_score
        self._baseline_tasks = [(t.task_id, t.score) for t in result.task_scores]
        self._update()

    def print_cycle(self, result: CycleResult) -> None:
        self._cycles.append(result)
        self._update()

    def print_plateau(self, cycle: int, patience: int) -> None:
        self._plateau_msg = f"Plateau at cycle {cycle} ({patience} cycles w/o improvement)"
        self._update()

    def print_summary(self, summary: SimSummary) -> None:
        if self._live:
            self._live.stop()
            self._live = None

        # Print final summary to console (static, scrollable)
        self.console.print()
        self.console.rule("[bold]Simulation Complete[/bold]")
        self._print_final_summary(summary)

    def _update(self) -> None:
        if self._live:
            self._live.update(self._build_layout())

    def _build_layout(self) -> Panel:
        """Compose all panels into a single renderable."""
        sections = []

        # Header
        sections.append(self._build_header())

        # Score bar
        sections.append(self._build_score_bar())

        # Middle row: mutation + stats side by side
        mid_layout = Layout()
        mid_layout.split_row(
            Layout(self._build_mutation_panel(), name="mutation"),
            Layout(self._build_stats_panel(), name="stats"),
        )
        mid_layout.minimum_size = 7
        sections.append(mid_layout)

        # Score history chart
        sections.append(self._build_chart_panel())

        # Cycle log table
        sections.append(self._build_cycle_table())

        # Plateau warning
        if self._plateau_msg:
            sections.append(
                Text(f"  {self._plateau_msg}", style="bold yellow")
            )

        return Panel(
            Group(*sections),
            title="[bold cyan]TaoForge Sim[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        )

    def _build_header(self) -> Text:
        elapsed = time.monotonic() - self._start_time if self._start_time else 0
        cycle_num = len(self._cycles)
        max_cycles = self._config.max_cycles if self._config else 0

        agent_name = ""
        if self._agent:
            cfg = self._agent.config
            if cfg.runtime == "api":
                agent_name = f"{cfg.api_provider}/{cfg.api_model}"
            else:
                agent_name = cfg.model_name_or_path or cfg.runtime

        mins, secs = divmod(int(elapsed), 60)
        time_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

        text = Text()
        text.append(f" Cycle {cycle_num}/{max_cycles}", style="bold")
        text.append("  |  ", style="dim")
        text.append(f"Agent: {agent_name}", style="bold white")
        text.append("  |  ", style="dim")
        text.append(f"Elapsed: {time_str}", style="bold white")
        return text

    def _build_score_bar(self) -> Text:
        if not self._cycles:
            score = self._baseline_score
            delta = 0.0
        else:
            last = self._cycles[-1]
            score = last.delta_score if last.accepted else last.baseline_score
            delta = last.raw_improvement

        bar_width = 40
        filled = int(score * bar_width)
        empty = bar_width - filled

        text = Text()
        text.append(" ")
        text.append("\u2588" * filled, style="bold green" if score >= 0.5 else "bold yellow")
        text.append("\u2591" * empty, style="dim")
        text.append(f" {score:.4f}", style="bold white")

        if delta != 0:
            delta_style = "bold green" if delta > 0 else "bold red"
            text.append(f" ({delta:+.4f})", style=delta_style)

        return text

    def _build_mutation_panel(self) -> Panel:
        if not self._cycles:
            content = Text("Waiting for first cycle...", style="dim italic")
        else:
            last = self._cycles[-1]
            content = Text()
            content.append(f"Type: {last.mutation_type}\n", style="white")
            content.append(f"Desc: {last.mutation_description}\n", style="dim")

            if last.accepted:
                content.append("Status: ACCEPTED", style="bold green")
            else:
                content.append("Status: REJECTED", style="bold red")

            if last.score_vector and last.score_vector.regression_flags:
                regs = ", ".join(last.score_vector.regression_flags)
                content.append(f"\nRegressions: {regs}", style="yellow")

        return Panel(content, title="[bold]Mutation[/bold]", border_style="blue", padding=(0, 1))

    def _build_stats_panel(self) -> Panel:
        accepted = sum(1 for c in self._cycles if c.accepted)
        total = len(self._cycles)
        rate = (accepted / total * 100) if total > 0 else 0

        # Compute streak (consecutive accepted from tail)
        streak = 0
        for c in reversed(self._cycles):
            if c.accepted:
                streak += 1
            else:
                break

        # DAG nodes = accepted count
        dag_nodes = accepted

        # Reputation estimate (sum of improvements from accepted cycles)
        rep = sum(c.raw_improvement for c in self._cycles if c.accepted)

        table = Table(show_header=False, show_edge=False, padding=(0, 1), expand=True)
        table.add_column("key", style="dim", ratio=1)
        table.add_column("val", style="bold white", ratio=1)
        table.add_row("DAG nodes", str(dag_nodes))
        table.add_row("Streak", str(streak))
        table.add_row("Reputation", f"{rep:.4f}")
        table.add_row("Accept rate", f"{rate:.0f}% ({accepted}/{total})")

        return Panel(table, title="[bold]Stats[/bold]", border_style="blue", padding=(0, 1))

    def _build_chart_panel(self) -> Panel:
        if not self._cycles:
            return Panel(
                Text("No data yet", style="dim italic"),
                title="[bold]Score History[/bold]",
                border_style="blue",
                padding=(0, 1),
            )

        chart = _render_score_chart(self._cycles, self._baseline_score)
        return Panel(chart, title="[bold]Score History[/bold]", border_style="blue", padding=(0, 1))

    def _build_cycle_table(self) -> Panel:
        table = Table(expand=True, padding=(0, 1))
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Mutation", ratio=2)
        table.add_column("Base", justify="right", width=8)
        table.add_column("Delta", justify="right", width=8)
        table.add_column("\u0394", justify="right", width=8)
        table.add_column("Score", justify="right", width=7)
        table.add_column("", width=2)

        # Show last 8 cycles
        visible = self._cycles[-8:]
        for c in visible:
            delta_str = f"{c.raw_improvement:+.4f}"
            delta_style = "green" if c.raw_improvement > 0 else "red"
            status = "[green]\u2713[/green]" if c.accepted else "[red]\u2717[/red]"

            # Truncate mutation type
            mt = c.mutation_type
            if len(mt) > 22:
                mt = mt[:20] + ".."

            table.add_row(
                str(c.cycle_num),
                mt,
                f"{c.baseline_score:.4f}",
                f"{c.delta_score:.4f}",
                f"[{delta_style}]{delta_str}[/{delta_style}]",
                f"{c.composite_score:.3f}",
                status,
            )

        return Panel(table, title="[bold]Cycle Log[/bold]", border_style="blue", padding=(0, 0))

    def _print_final_summary(self, summary: SimSummary) -> None:
        improvement_pct = (
            summary.total_improvement / summary.initial_score * 100
            if summary.initial_score > 0 else 0.0
        )

        table = Table(show_header=False, padding=(0, 2), expand=True)
        table.add_column("key", style="dim")
        table.add_column("val", style="bold")

        table.add_row("Cycles", f"{summary.total_cycles} ({summary.accepted_count} accepted, {summary.rejected_count} rejected)")
        table.add_row("Score", f"{summary.initial_score:.4f} -> {summary.final_score:.4f} ({summary.total_improvement:+.4f}, {improvement_pct:+.1f}%)")
        table.add_row("Best composite", f"{summary.best_composite_score:.4f}")
        table.add_row("DAG depth", str(summary.dag_depth))
        table.add_row("Reputation", f"{summary.reputation:.4f}")
        table.add_row("Time", f"{summary.elapsed_s:.1f}s")

        self.console.print(table)

        if summary.mutation_stats:
            self.console.print()
            mt_table = Table(title="Mutation Stats", expand=True)
            mt_table.add_column("Mutation", style="cyan")
            mt_table.add_column("Accepted", justify="right")
            mt_table.add_column("Attempted", justify="right")
            mt_table.add_column("Rate", justify="right")
            mt_table.add_column("Improvement", justify="right")

            for mt, stats in sorted(summary.mutation_stats.items()):
                rate = stats["accepted"] / stats["attempted"] * 100 if stats["attempted"] > 0 else 0
                mt_table.add_row(
                    mt,
                    str(stats["accepted"]),
                    str(stats["attempted"]),
                    f"{rate:.0f}%",
                    f"{stats['total_improvement']:+.4f}",
                )

            self.console.print(mt_table)

    def __del__(self) -> None:
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass


def _render_score_chart(cycles: list[CycleResult], baseline: float) -> Text:
    """Render an ASCII line chart of score history."""
    height = 8
    width = min(len(cycles) + 1, 50)

    # Collect scores (baseline + each cycle's effective score)
    scores = [baseline]
    accepted_flags = [True]  # baseline is always "accepted"
    current = baseline
    for c in cycles:
        if c.accepted:
            current = c.delta_score
        scores.append(c.delta_score)
        accepted_flags.append(c.accepted)

    # Only show last `width` points
    if len(scores) > width:
        scores = scores[-width:]
        accepted_flags = accepted_flags[-width:]

    min_score = min(scores) - 0.02
    max_score = max(scores) + 0.02
    score_range = max_score - min_score
    if score_range < 0.01:
        score_range = 0.01

    # Build chart grid
    grid = [[" " for _ in range(len(scores))] for _ in range(height)]

    for col, (score, is_accepted) in enumerate(zip(scores, accepted_flags)):
        row = height - 1 - int((score - min_score) / score_range * (height - 1))
        row = max(0, min(height - 1, row))
        grid[row][col] = "*" if is_accepted else "x"

    # Render
    text = Text()
    for row_idx in range(height):
        # Y-axis label (show at top, middle, bottom)
        if row_idx == 0:
            label = f"{max_score:.3f}"
        elif row_idx == height - 1:
            label = f"{min_score:.3f}"
        elif row_idx == height // 2:
            mid = (max_score + min_score) / 2
            label = f"{mid:.3f}"
        else:
            label = "     "

        text.append(f" {label}\u2502", style="dim")

        for col in range(len(scores)):
            ch = grid[row_idx][col]
            if ch == "*":
                text.append(ch, style="bold green")
            elif ch == "x":
                text.append(ch, style="bold red")
            else:
                text.append(ch)

        text.append("\n")

    # X-axis
    text.append(f"      \u2514", style="dim")
    text.append("\u2500" * len(scores), style="dim")

    return text
