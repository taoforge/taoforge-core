"""Base validator neuron — async loop for querying miners and tracking scores."""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from pathlib import Path

from taoforge.base.config import ValidatorConfig
from taoforge.base.neuron import BaseNeuron
from taoforge.net.client import ValidatorClient
from taoforge.proposal.schema import ImprovementProposal
from taoforge.registry.dag import ImprovementDAG
from taoforge.registry.reputation import ReputationSystem

logger = logging.getLogger(__name__)


class BaseValidatorNeuron(BaseNeuron):
    """Base class for TaoForge validator neurons.

    Maintains an HTTP client, score tracking, and runs the
    forward/score loop.
    """

    neuron_type = "Validator"

    def __init__(self, config: ValidatorConfig) -> None:
        super().__init__(config)
        self.validator_config = config

        # HTTP client for querying miners
        self.client = ValidatorClient(keypair=self.keypair)

        # Score tracking — per-miner moving average
        self._scores: dict[str, float] = {}
        self.moving_avg_alpha = 0.1

        # Improvement DAG, reputation, and proposal history
        self.dag = ImprovementDAG()
        self.reputation = ReputationSystem(decay_rate=0.01)
        self.proposal_history: list[ImprovementProposal] = []

        logger.info(
            f"Initialized Validator | node_id={self.keypair.node_id} | "
            f"tracking {self.peers.active_count} peers"
        )

    def run(self) -> None:
        """Main validator loop: query miners, score, repeat."""
        logger.info("Validator starting main loop.")
        asyncio.run(self._run_loop())

    async def _run_loop(self) -> None:
        """Async main loop."""
        try:
            while not self.should_exit:
                miners = self.peers.get_miners()
                if miners:
                    await self.forward(miners)

                # Send heartbeats periodically
                if self.step % 10 == 0:
                    await self._send_heartbeats()

                self.step += 1
                await asyncio.sleep(self.validator_config.query_interval)

        except KeyboardInterrupt:
            logger.info("Validator interrupted by user.")
        except Exception:
            logger.error(f"Validator error:\n{traceback.format_exc()}")

    async def forward(self, miners: list) -> None:
        """Execute one forward pass — query miners, score responses.

        Override in subclass or use taoforge.forward.forward_fn.
        """
        logger.debug(f"Forward pass for {len(miners)} miners — not yet implemented.")

    def update_scores(self, miner_scores: dict[str, float]) -> None:
        """Update moving average scores for queried miners."""
        for node_id, score in miner_scores.items():
            prev = self._scores.get(node_id, 0.0)
            self._scores[node_id] = (
                self.moving_avg_alpha * score
                + (1 - self.moving_avg_alpha) * prev
            )

    def get_scores(self) -> dict[str, float]:
        """Get current miner scores."""
        return dict(self._scores)

    def get_rankings(self) -> list[tuple[str, float]]:
        """Get miners ranked by score (descending)."""
        return sorted(self._scores.items(), key=lambda x: x[1], reverse=True)

    async def _send_heartbeats(self) -> None:
        """Send heartbeats to all known peers."""
        self_info = {
            "node_id": self.keypair.node_id,
            "host": self.config.host,
            "port": self.config.port,
            "role": "validator",
            "public_key": self.keypair.public_key_hex,
        }
        for peer in self.peers.get_all_active():
            await self.client.send_heartbeat(peer, self_info)

    def save_state(self) -> None:
        """Persist scores to disk."""
        state_path = Path("~/.taoforge/validator_state.json").expanduser()
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "scores": self._scores,
            "dag_size": self.dag.size,
            "reputation_count": len(self.reputation._records),
        }
        state_path.write_text(json.dumps(state, indent=2))

    def load_state(self) -> None:
        """Load scores from disk."""
        state_path = Path("~/.taoforge/validator_state.json").expanduser()
        try:
            state = json.loads(state_path.read_text())
            self._scores = state.get("scores", {})
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No saved validator state found — starting fresh.")
