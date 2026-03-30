"""CLI entry point for TaoForge simulation.

Usage:
    python -m taoforge.sim                          # Run with defaults
    python -m taoforge.sim --model gpt-4o-mini      # API agent
    python -m taoforge.sim --local microsoft/phi-3   # Local LLM
    python -m taoforge.sim --cycles 50 --json       # JSON output, 50 cycles
"""

from __future__ import annotations

import argparse
import logging
import sys

from taoforge.agent.base import AgentConfig
from taoforge.sim.runner import SimConfig, SimulationRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="taoforge-sim",
        description="TaoForge Simulation — dry-run the self-improvement cycle locally.",
    )

    # Agent selection
    agent_group = parser.add_mutually_exclusive_group()
    agent_group.add_argument(
        "--local", metavar="MODEL",
        help="Use a local LLM (HuggingFace model name or path).",
    )
    agent_group.add_argument(
        "--model", metavar="MODEL",
        help="Use an API model (e.g., gpt-4o-mini, claude-sonnet-4-20250514).",
    )

    # API settings
    parser.add_argument("--provider", default="openai", choices=["openai", "anthropic"],
                        help="API provider (default: openai).")
    parser.add_argument("--api-key", default="", help="API key (or use env var).")

    # Simulation settings
    parser.add_argument("--cycles", type=int, default=20, help="Max improvement cycles (default: 20).")
    parser.add_argument("--patience", type=int, default=5, help="Plateau patience (default: 5).")
    parser.add_argument("--no-plateau", action="store_true", help="Disable plateau detection.")

    # Output
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout.")
    parser.add_argument("--tui", action="store_true", help="Live terminal dashboard (requires 'rich').")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress all non-essential output.")

    # Checkpointing
    parser.add_argument("--checkpoint", metavar="DIR", help="Save agent checkpoint on completion.")

    # Device
    parser.add_argument("--device", default="auto", help="Device for local models (default: auto).")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Build agent config
    if args.local:
        agent_config = AgentConfig(
            runtime="local_llm",
            model_name_or_path=args.local,
            device=args.device,
        )
    elif args.model:
        agent_config = AgentConfig(
            runtime="api",
            api_provider=args.provider,
            api_model=args.model,
            api_key=args.api_key,
        )
    else:
        # Default: require explicit model selection
        print(
            "Error: specify an agent with --model (API) or --local (LLM).\n"
            "\n"
            "Examples:\n"
            "  taoforge-sim --model gpt-4o-mini\n"
            "  taoforge-sim --model claude-sonnet-4-20250514 --provider anthropic\n"
            "  taoforge-sim --local microsoft/phi-3-mini-4k-instruct\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build sim config
    sim_config = SimConfig(
        max_cycles=args.cycles,
        stop_on_plateau=not args.no_plateau,
        plateau_patience=args.patience,
        agent_config=agent_config,
        json_output=args.json,
        verbose=not args.quiet,
        checkpoint_dir=args.checkpoint,
    )

    # Build reporter
    reporter = None
    if args.tui:
        try:
            from taoforge.sim.tui import TuiReporter
            reporter = TuiReporter(json_mode=args.json)
        except ImportError:
            print("Warning: --tui requires 'rich'. Install with: pip install taoforge[tui]",
                  file=sys.stderr)

    # Run
    runner = SimulationRunner(sim_config, reporter=reporter)
    summary = runner.run()

    # Exit code based on improvement
    if summary.total_improvement > 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
