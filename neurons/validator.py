"""TaoForge Validator — entry point for the validator neuron.

Validators query miners, re-run benchmarks, verify ZK proofs, and score proposals.
"""

from __future__ import annotations

import logging

from taoforge.base.config import ValidatorConfig
from taoforge.base.validator import BaseValidatorNeuron
from taoforge.forward import forward_fn
from taoforge.net.peer import PeerInfo

logger = logging.getLogger(__name__)


class TaoForgeValidator(BaseValidatorNeuron):
    """TaoForge validator: evaluates and scores improvement proposals."""

    def __init__(self, config: ValidatorConfig) -> None:
        super().__init__(config)
        self.load_state()

    async def forward(self, miners: list[PeerInfo]) -> None:
        """Execute one forward pass — delegates to forward_fn."""
        scores = await forward_fn(self, miners)

        # Log rankings periodically
        if self.step % 5 == 0:
            rankings = self.get_rankings()
            if rankings:
                top = rankings[:5]
                logger.info(
                    f"Top miners (step {self.step}): "
                    + ", ".join(f"{nid[:8]}={s:.4f}" for nid, s in top)
                )

            # Log DAG stats
            logger.info(
                f"DAG: {self.dag.size} nodes | "
                f"{self.dag.agent_count} agents | "
                f"depth={self.dag.max_depth} | "
                f"frontier={len(self.dag.get_frontier())}"
            )

        # Persist state periodically
        if self.step % 10 == 0:
            self.save_state()


def main() -> None:
    """Entry point for the TaoForge validator."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="TaoForge Validator")
    parser.add_argument("--port", type=int, default=None, help="Override listen port")
    parser.add_argument("--host", type=str, default=None, help="Override listen host")
    parser.add_argument("--seed-peers", type=str, nargs="*", default=None,
                        help="Seed peers (host:port)")
    parser.add_argument("--query-interval", type=float, default=None,
                        help="Seconds between query rounds (default: 12)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = ValidatorConfig()
    if args.port:
        config.port = args.port
    if args.host:
        config.host = args.host
    if args.seed_peers:
        config.seed_peers = args.seed_peers
    if args.query_interval:
        config.query_interval = args.query_interval

    validator = TaoForgeValidator(config)
    validator.run()


if __name__ == "__main__":
    main()
