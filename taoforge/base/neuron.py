"""Base neuron class — shared infrastructure for miners and validators."""

from __future__ import annotations

import abc
import logging
from pathlib import Path

from taoforge.base.config import NodeConfig
from taoforge.net.auth import Keypair
from taoforge.net.peer import PeerInfo, PeerRegistry

logger = logging.getLogger(__name__)


class BaseNeuron(abc.ABC):
    """Common base for all TaoForge neurons.

    Handles keypair loading, peer registry, and configuration.
    """

    neuron_type: str = "BaseNeuron"

    def __init__(self, config: NodeConfig) -> None:
        self.config = config

        # Load or create node keypair
        key_path = Path(config.key_file).expanduser()
        self.keypair = Keypair.load_or_create(key_path)

        # Peer registry
        self.peers = PeerRegistry()

        # Register seed peers
        for seed in config.seed_peers:
            self._register_seed_peer(seed)

        self.step = 0
        self._should_exit = False

        logger.info(
            f"Initialized {self.neuron_type} | node_id={self.keypair.node_id} | "
            f"host={config.host}:{config.port}"
        )

    def _register_seed_peer(self, seed: str) -> None:
        """Register a seed peer from a host:port string."""
        try:
            host, port_str = seed.rsplit(":", 1)
            port = int(port_str)
            from taoforge.net.peer import NodeRole
            self.peers.register(PeerInfo(
                node_id=f"seed_{host}_{port}",
                host=host,
                port=port,
                role=NodeRole.VALIDATOR,  # Default; will be updated on handshake
            ))
        except ValueError:
            logger.warning(f"Invalid seed peer format: {seed} (expected host:port)")

    @property
    def should_exit(self) -> bool:
        return self._should_exit

    @should_exit.setter
    def should_exit(self, value: bool) -> None:
        self._should_exit = value

    @abc.abstractmethod
    def run(self) -> None:
        """Main neuron loop — must be implemented by subclasses."""
        ...

    def save_state(self) -> None:
        """Persist neuron state to disk. Override in subclasses."""
        pass

    def load_state(self) -> None:
        """Load neuron state from disk. Override in subclasses."""
        pass
