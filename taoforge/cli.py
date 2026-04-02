"""Unified TaoForge CLI — single entry point for all protocol operations.

Usage:
    taoforge sim [options]       Run a local simulation (petri dish)
    taoforge miner [options]     Start a miner node
    taoforge validator [options] Start a validator node
    taoforge status              Show node/network status
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="taoforge",
        description="TaoForge — Recursive Self-Improvement Protocol",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- sim ---
    sim_parser = subparsers.add_parser("sim", help="Run a local simulation (petri dish)")
    sim_parser.add_argument("--model", type=str, default="gpt-4o-mini",
                            help="Model name (API) or path (local)")
    sim_parser.add_argument("--local", action="store_true",
                            help="Use local LLM instead of API")
    sim_parser.add_argument("--provider", type=str, default="openai",
                            choices=["openai", "anthropic"],
                            help="API provider (default: openai)")
    sim_parser.add_argument("--cycles", type=int, default=20,
                            help="Max improvement cycles (default: 20)")
    sim_parser.add_argument("--patience", type=int, default=5,
                            help="Plateau patience (default: 5)")
    sim_parser.add_argument("--json", action="store_true",
                            help="Output results as JSON")
    sim_parser.add_argument("--tui", action="store_true",
                            help="Live terminal dashboard (requires 'rich')")
    sim_parser.add_argument("--device", type=str, default="auto",
                            help="Device for local models (auto/cuda/cpu)")
    sim_parser.add_argument("--checkpoint", type=str, default=None,
                            help="Directory to save agent checkpoint")
    sim_parser.add_argument("--environment", type=str, default=None,
                            choices=["subnet"],
                            help="Open-ended environment to explore (e.g. 'subnet')")
    sim_parser.add_argument("--subnet-analysis", action="store_true",
                            help="Use subnet analysis environment (alias for --environment subnet)")
    sim_parser.add_argument("--netuid", type=int, default=1,
                            help="Subnet to analyze (default: 1)")

    # --- miner ---
    miner_parser = subparsers.add_parser("miner", help="Start a miner node")
    miner_parser.add_argument("--model", type=str, default="",
                              help="Model name/path")
    miner_parser.add_argument("--provider", type=str, default="",
                              choices=["openai", "anthropic", "local", ""],
                              help="Agent provider")
    miner_parser.add_argument("--device", type=str, default="auto",
                              help="Device for local LLM")
    miner_parser.add_argument("--port", type=int, default=8091,
                              help="Listen port (default: 8091)")
    miner_parser.add_argument("--host", type=str, default="0.0.0.0",
                              help="Listen host (default: 0.0.0.0)")
    miner_parser.add_argument("--seed-peers", type=str, nargs="*", default=[],
                              help="Seed peers (host:port)")

    # --- validator ---
    val_parser = subparsers.add_parser("validator", help="Start a validator node")
    val_parser.add_argument("--port", type=int, default=8092,
                            help="Listen port (default: 8092)")
    val_parser.add_argument("--host", type=str, default="0.0.0.0",
                            help="Listen host (default: 0.0.0.0)")
    val_parser.add_argument("--seed-peers", type=str, nargs="*", default=[],
                            help="Seed peers (host:port)")
    val_parser.add_argument("--query-interval", type=float, default=12.0,
                            help="Seconds between query rounds (default: 12)")

    # --- batch ---
    batch_parser = subparsers.add_parser("batch", help="Run multiple agent sims sequentially")
    batch_parser.add_argument("--agents", type=int, default=10,
                              help="Number of agent runs (default: 10)")
    batch_parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct",
                              help="Model name (API) or path (local)")
    batch_parser.add_argument("--local", action="store_true",
                              help="Use local LLM instead of API")
    batch_parser.add_argument("--provider", type=str, default="openai",
                              choices=["openai", "anthropic"],
                              help="API provider (default: openai)")
    batch_parser.add_argument("--cycles", type=int, default=20,
                              help="Max cycles per agent (default: 20)")
    batch_parser.add_argument("--patience", type=int, default=5,
                              help="Plateau patience (default: 5)")
    batch_parser.add_argument("--sweep", action="store_true",
                              help="Auto-vary mutation weights across runs")
    batch_parser.add_argument("--device", type=str, default="auto",
                              help="Device for local models (auto/cuda/cpu)")
    batch_parser.add_argument("--tui", action="store_true",
                              help="Show TUI for each run")
    batch_parser.add_argument("--results-dir", type=str, default="batch_results",
                              help="Directory for results (default: batch_results)")
    batch_parser.add_argument("--environment", type=str, default=None,
                              choices=["subnet"],
                              help="Open-ended environment to explore (e.g. 'subnet')")
    batch_parser.add_argument("--subnet-analysis", action="store_true",
                              help="Use subnet analysis environment (alias for --environment subnet)")
    batch_parser.add_argument("--netuid", type=int, default=1,
                              help="Subnet to analyze (default: 1)")
    batch_parser.add_argument("--dashboard", action="store_true",
                              help="Start live dashboard API server during batch run")
    batch_parser.add_argument("--dashboard-port", type=int, default=8092,
                              help="Dashboard API port (default: 8092)")
    batch_parser.add_argument("--dashboard-host", type=str, default="0.0.0.0",
                              help="Dashboard API host (default: 0.0.0.0 — public)")
    batch_parser.add_argument("--push-results", action="store_true",
                              help="Push results to GitHub → auto-deploy to Vercel when batch completes")
    batch_parser.add_argument("--github-token", type=str, default="",
                              help="GitHub PAT for pushing results (or set GITHUB_TOKEN env var)")
    batch_parser.add_argument("--github-repo", type=str, default="taoforge/taoforge-web",
                              help="GitHub repo to push results to (default: taoforge/taoforge-web)")

    # --- status ---
    subparsers.add_parser("status", help="Show node and network status")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "sim":
        _run_sim(args)
    elif args.command == "batch":
        _run_batch(args)
    elif args.command == "miner":
        _run_miner(args)
    elif args.command == "validator":
        _run_validator(args)
    elif args.command == "status":
        _run_status(args)


def _run_sim(args: argparse.Namespace) -> None:
    """Run the simulation harness."""
    import logging

    from taoforge.agent.base import AgentConfig
    from taoforge.sim.runner import SimConfig, SimulationRunner

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    use_env_sim = args.environment or ("subnet" if args.subnet_analysis else None)
    subnet_system_prompt = (
        "You are a rigorous blockchain data analyst specializing in Bittensor subnet metagraphs. "
        "When analyzing subnet data, you always reference specific UIDs by number, cite exact stake "
        "and incentive values, calculate concentration metrics, and identify structural patterns "
        "in validator-miner relationships. You ground every claim in the data."
    )

    if args.local:
        agent_config = AgentConfig(
            runtime="local_llm",
            model_name_or_path=args.model,
            device=args.device,
            system_prompt=subnet_system_prompt if use_env_sim == "subnet" else "",
        )
    else:
        agent_config = AgentConfig(
            runtime="api",
            api_provider=args.provider,
            api_model=args.model,
            system_prompt=subnet_system_prompt if use_env_sim == "subnet" else "You are a helpful assistant.",
        )

    sim_config = SimConfig(
        max_cycles=args.cycles,
        plateau_patience=args.patience,
        agent_config=agent_config,
        json_output=args.json,
        checkpoint_dir=args.checkpoint,
    )

    reporter = None
    if args.tui:
        try:
            from taoforge.sim.tui import TuiReporter
            reporter = TuiReporter(json_mode=args.json)
        except ImportError:
            print("Warning: --tui requires 'rich'. Install with: pip install taoforge[tui]",
                  file=sys.stderr)

    # Resolve environment (--environment subnet or --subnet-analysis are equivalent)
    use_env = args.environment or ("subnet" if args.subnet_analysis else None)

    evaluator = None
    if use_env == "subnet":
        from taoforge.subnets.analysis_adapter import SubnetAnalysisAdapter
        from taoforge.subnets.registry import SubnetProfile, SubnetDomain

        profile = SubnetProfile(
            netuid=args.netuid,
            name=f"SN{args.netuid}",
            domain=SubnetDomain.DATA,
            benchmark_type="subnet_analysis",
        )
        adapter = SubnetAnalysisAdapter(profile)
        # Pass adapter.evaluate_locally as the evaluator — uses EnvironmentHarness internally
        evaluator = adapter.evaluate_locally

    runner = SimulationRunner(sim_config, reporter=reporter, evaluator=evaluator)
    runner.run()


def _run_batch(args: argparse.Namespace) -> None:
    """Run multiple agent sims sequentially."""
    import logging

    from taoforge.agent.base import AgentConfig
    from taoforge.sim.batch import BatchConfig, BatchRunner
    from taoforge.sim.runner import SimConfig

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Resolve environment early so we can set the right system prompt
    use_env = args.environment or ("subnet" if args.subnet_analysis else None)

    subnet_system_prompt = (
        "You are a rigorous blockchain data analyst specializing in Bittensor subnet metagraphs. "
        "When analyzing subnet data, you always reference specific UIDs by number, cite exact stake "
        "and incentive values, calculate concentration metrics, and identify structural patterns "
        "in validator-miner relationships. You ground every claim in the data."
    )

    if args.local:
        agent_config = AgentConfig(
            runtime="local_llm",
            model_name_or_path=args.model,
            device=args.device,
            system_prompt=subnet_system_prompt if use_env == "subnet" else "",
        )
    else:
        agent_config = AgentConfig(
            runtime="api",
            api_provider=args.provider,
            api_model=args.model,
            system_prompt=subnet_system_prompt if use_env == "subnet" else "You are a helpful assistant.",
        )

    sim_config = SimConfig(
        max_cycles=args.cycles,
        plateau_patience=args.patience,
        json_output=False,
        verbose=False,
    )

    evaluator = None
    if use_env == "subnet":
        from taoforge.subnets.analysis_adapter import SubnetAnalysisAdapter
        from taoforge.subnets.registry import SubnetProfile, SubnetDomain

        profile = SubnetProfile(
            netuid=args.netuid,
            name=f"SN{args.netuid}",
            domain=SubnetDomain.DATA,
            benchmark_type="subnet_analysis",
        )
        adapter = SubnetAnalysisAdapter(profile)
        evaluator = adapter.evaluate_locally

    # Start live dashboard server if requested
    dashboard = None
    if getattr(args, "dashboard", False):
        from taoforge.net.dashboard import DashboardState, create_dashboard_app
        import threading
        import uvicorn

        dashboard = DashboardState()
        app = create_dashboard_app(dashboard)

        def _serve():
            uvicorn.run(
                app,
                host=args.dashboard_host,
                port=args.dashboard_port,
                log_level="warning",
            )

        t = threading.Thread(target=_serve, daemon=True)
        t.start()

        host_display = args.dashboard_host if args.dashboard_host != "0.0.0.0" else "<your-ip>"
        print(
            f"\n  Dashboard live at: http://{host_display}:{args.dashboard_port}\n"
            f"  SSE stream:        http://{host_display}:{args.dashboard_port}/events/stream\n",
            file=sys.stderr,
        )

    # Resolve GitHub token for auto-push
    import os
    github_token = args.github_token or (os.environ.get("GITHUB_TOKEN", "") if args.push_results else "")

    batch_config = BatchConfig(
        num_agents=args.agents,
        base_agent_config=agent_config,
        base_sim_config=sim_config,
        sweep=args.sweep,
        evaluator=evaluator,
        results_dir=args.results_dir,
        use_tui=args.tui,
        github_token=github_token,
        github_repo=args.github_repo,
    )

    runner = BatchRunner(batch_config, dashboard=dashboard)
    summary = runner.run()

    sys.exit(0 if summary.improved > 0 else 1)


def _run_miner(args: argparse.Namespace) -> None:
    """Start a miner node."""
    import logging

    from taoforge.agent.base import AgentConfig
    from taoforge.base.config import MinerConfig
    from neurons.miner import TaoForgeMiner

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = MinerConfig()
    config.port = args.port
    config.host = args.host
    if args.seed_peers:
        config.seed_peers = args.seed_peers

    miner = TaoForgeMiner(config)

    provider = args.provider
    model = args.model

    if provider in ("openai", "anthropic"):
        agent_config = AgentConfig(
            runtime="api",
            api_provider=provider,
            api_model=model or ("gpt-4o-mini" if provider == "openai" else "claude-sonnet-4-6"),
            system_prompt="You are a helpful assistant.",
        )
        miner.load_agent(agent_config)
    elif provider == "local" or (model and not provider):
        agent_config = AgentConfig(
            runtime="local_llm",
            model_name_or_path=model or "microsoft/phi-3-mini-4k-instruct",
            device=args.device,
        )
        miner.load_agent(agent_config)

    miner.run()


def _run_validator(args: argparse.Namespace) -> None:
    """Start a validator node."""
    import logging

    from taoforge.base.config import ValidatorConfig
    from neurons.validator import TaoForgeValidator

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = ValidatorConfig()
    config.port = args.port
    config.host = args.host
    if args.seed_peers:
        config.seed_peers = args.seed_peers
    config.query_interval = args.query_interval

    validator = TaoForgeValidator(config)
    validator.run()


def _run_status(args: argparse.Namespace) -> None:
    """Show node and network status."""
    import json
    from pathlib import Path

    print("TaoForge Status")
    print("=" * 50)

    # Check for keypair
    key_path = Path("~/.taoforge/node.key").expanduser()
    if key_path.exists():
        from taoforge.net.auth import Keypair
        kp = Keypair.from_file(key_path)
        print(f"  Node ID:    {kp.node_id}")
        print(f"  Public Key: {kp.public_key_hex}")
    else:
        print("  No node keypair found (will be created on first run)")

    # Check for validator state
    state_path = Path("~/.taoforge/validator_state.json").expanduser()
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            print(f"\nValidator State:")
            print(f"  Tracked miners: {len(state.get('scores', {}))}")
            print(f"  DAG nodes:      {state.get('dag_size', 0)}")
            scores = state.get("scores", {})
            if scores:
                top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"  Top miners:")
                for nid, score in top:
                    print(f"    {nid[:16]}: {score:.4f}")
        except (json.JSONDecodeError, KeyError):
            print("  Validator state file exists but is corrupted")
    else:
        print("\n  No validator state found")

    print()


if __name__ == "__main__":
    main()
