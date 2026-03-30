"""Async HTTP client for validators — replaces bt.dendrite."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from taoforge.net.auth import Keypair, sign_request
from taoforge.net.peer import PeerInfo

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0


class ValidatorClient:
    """Async HTTP client for querying miners.

    Replaces bt.dendrite — uses httpx to POST challenges to miner
    FastAPI servers and collect responses.
    """

    def __init__(self, keypair: Keypair, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.keypair = keypair
        self.timeout = timeout

    async def query_miner(
        self,
        peer: PeerInfo,
        endpoint: str,
        data: dict,
    ) -> dict[str, Any] | None:
        """Send a challenge to a single miner and return the response.

        Args:
            peer: The miner peer to query.
            endpoint: API endpoint (e.g., "/v1/proposal").
            data: JSON payload.

        Returns:
            Response dict, or None on failure.
        """
        url = f"{peer.address}{endpoint}"
        body = httpx._content.json_dumps(data) if isinstance(data, dict) else data

        # Sign request
        headers = sign_request(self.keypair, "POST", endpoint, body if isinstance(body, bytes) else body.encode())
        headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, content=body, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            logger.warning(f"Timeout querying miner {peer.node_id} at {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} from miner {peer.node_id}")
            return None
        except Exception as e:
            logger.error(f"Error querying miner {peer.node_id}: {e}")
            return None

    async def query_miners(
        self,
        peers: list[PeerInfo],
        endpoint: str,
        data: dict,
    ) -> list[dict[str, Any] | None]:
        """Query multiple miners concurrently.

        Args:
            peers: List of miner peers to query.
            endpoint: API endpoint.
            data: JSON payload (same for all miners).

        Returns:
            List of responses (None for failed queries), one per peer.
        """
        tasks = [self.query_miner(peer, endpoint, data) for peer in peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception querying {peers[i].node_id}: {result}")
                processed.append(None)
            else:
                processed.append(result)

        logger.info(
            f"Queried {len(peers)} miners | "
            f"{sum(1 for r in processed if r is not None)} responded"
        )
        return processed

    async def send_heartbeat(self, peer: PeerInfo, self_info: dict) -> bool:
        """Send a heartbeat to a peer. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{peer.address}/v1/heartbeat",
                    json=self_info,
                )
                return response.status_code == 200
        except Exception:
            return False
