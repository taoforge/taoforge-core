"""Peer registry — discovery and heartbeat for TaoForge nodes."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    MINER = "miner"
    VALIDATOR = "validator"


@dataclass
class PeerInfo:
    """Information about a known peer."""

    node_id: str
    host: str
    port: int
    role: NodeRole
    public_key_hex: str = ""
    last_seen: float = field(default_factory=time.time)
    is_active: bool = True
    metadata: dict = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def age_seconds(self) -> float:
        return time.time() - self.last_seen


class PeerRegistry:
    """In-memory registry of known peers with heartbeat tracking.

    Replaces bt.metagraph — no chain required.
    """

    def __init__(self, stale_threshold: float = 120.0) -> None:
        self._peers: dict[str, PeerInfo] = {}
        self._lock = threading.Lock()
        self.stale_threshold = stale_threshold

    def register(self, peer: PeerInfo) -> None:
        """Register or update a peer."""
        with self._lock:
            self._peers[peer.node_id] = peer
            logger.debug(f"Peer registered: {peer.node_id} ({peer.role.value}) at {peer.address}")

    def heartbeat(self, node_id: str) -> bool:
        """Update last_seen for a peer. Returns False if peer unknown."""
        with self._lock:
            peer = self._peers.get(node_id)
            if peer is None:
                return False
            peer.last_seen = time.time()
            peer.is_active = True
            return True

    def remove(self, node_id: str) -> None:
        """Remove a peer."""
        with self._lock:
            self._peers.pop(node_id, None)

    def get_peer(self, node_id: str) -> PeerInfo | None:
        return self._peers.get(node_id)

    def get_miners(self) -> list[PeerInfo]:
        """Get all active miner peers."""
        self._mark_stale()
        with self._lock:
            return [
                p for p in self._peers.values()
                if p.role == NodeRole.MINER and p.is_active
            ]

    def get_validators(self) -> list[PeerInfo]:
        """Get all active validator peers."""
        self._mark_stale()
        with self._lock:
            return [
                p for p in self._peers.values()
                if p.role == NodeRole.VALIDATOR and p.is_active
            ]

    def get_all_active(self) -> list[PeerInfo]:
        self._mark_stale()
        with self._lock:
            return [p for p in self._peers.values() if p.is_active]

    def _mark_stale(self) -> None:
        """Mark peers as inactive if they haven't been seen recently."""
        with self._lock:
            now = time.time()
            for peer in self._peers.values():
                if now - peer.last_seen > self.stale_threshold:
                    if peer.is_active:
                        peer.is_active = False
                        logger.info(f"Peer stale: {peer.node_id} (no heartbeat for {peer.age_seconds:.0f}s)")

    @property
    def size(self) -> int:
        return len(self._peers)

    @property
    def active_count(self) -> int:
        self._mark_stale()
        with self._lock:
            return sum(1 for p in self._peers.values() if p.is_active)
