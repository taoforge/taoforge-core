"""Base miner neuron — FastAPI server for receiving validator requests."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from taoforge.base.config import MinerConfig
from taoforge.base.neuron import BaseNeuron
from taoforge.net.server import create_miner_app

logger = logging.getLogger(__name__)


class BaseMinerNeuron(BaseNeuron):
    """Base class for TaoForge miner neurons.

    Runs a FastAPI server that exposes proposal and benchmark endpoints
    for validators to query.
    """

    neuron_type = "Miner"

    def __init__(self, config: MinerConfig) -> None:
        super().__init__(config)
        self.miner_config = config

        # Create FastAPI app — handlers will be set by subclass
        self.app: FastAPI | None = None

    def _build_app(self) -> FastAPI:
        """Build the FastAPI app with handlers. Called by subclass after setup."""
        return create_miner_app(
            keypair=self.keypair,
            peer_registry=self.peers,
            proposal_handler=getattr(self, "handle_proposal", None),
            benchmark_handler=getattr(self, "handle_benchmark", None),
        )

    def run(self) -> None:
        """Run the miner FastAPI server."""
        self.app = self._build_app()

        logger.info(
            f"Miner starting | node_id={self.keypair.node_id} | "
            f"listening on {self.config.host}:{self.config.port}"
        )

        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level=self.config.log_level.lower(),
        )
