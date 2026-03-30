"""FastAPI miner server — replaces bt.axon for standalone protocol."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request, Response

from taoforge.net.auth import Keypair, verify_request
from taoforge.net.peer import NodeRole, PeerInfo, PeerRegistry

logger = logging.getLogger(__name__)


def create_miner_app(
    keypair: Keypair,
    peer_registry: PeerRegistry,
    proposal_handler: Callable | None = None,
    benchmark_handler: Callable | None = None,
) -> FastAPI:
    """Create a FastAPI app for the miner server.

    Args:
        keypair: This miner's keypair for identity.
        peer_registry: Registry of known peers.
        proposal_handler: Async handler for proposal challenges.
        benchmark_handler: Async handler for benchmark challenges.

    Returns:
        Configured FastAPI app.
    """
    app = FastAPI(title="TaoForge Miner", version="0.1.0")

    @app.get("/health")
    async def health():
        return {"status": "ok", "node_id": keypair.node_id, "role": "miner"}

    @app.post("/v1/proposal")
    async def handle_proposal(request: Request):
        """Handle an improvement proposal challenge from a validator."""
        body = await request.body()

        # Verify request signature
        if not _verify_caller(request, body):
            return Response(status_code=401, content="Invalid signature")

        if proposal_handler is None:
            return {"error": "Proposal handler not configured"}

        data = await request.json()
        result = await proposal_handler(data)
        return result

    @app.post("/v1/benchmark")
    async def handle_benchmark(request: Request):
        """Handle a benchmark challenge for re-evaluation."""
        body = await request.body()

        if not _verify_caller(request, body):
            return Response(status_code=401, content="Invalid signature")

        if benchmark_handler is None:
            return {"error": "Benchmark handler not configured"}

        data = await request.json()
        result = await benchmark_handler(data)
        return result

    @app.post("/v1/heartbeat")
    async def heartbeat(request: Request):
        """Heartbeat endpoint for peer liveness."""
        data = await request.json()
        node_id = data.get("node_id", "")

        if node_id:
            if not peer_registry.heartbeat(node_id):
                # Auto-register new peers from heartbeat
                peer_registry.register(PeerInfo(
                    node_id=node_id,
                    host=data.get("host", ""),
                    port=data.get("port", 0),
                    role=NodeRole(data.get("role", "validator")),
                    public_key_hex=data.get("public_key", ""),
                ))

        return {"status": "ok", "node_id": keypair.node_id}

    @app.get("/v1/peers")
    async def list_peers():
        """List known active peers."""
        return {
            "peers": [
                {
                    "node_id": p.node_id,
                    "host": p.host,
                    "port": p.port,
                    "role": p.role.value,
                    "is_active": p.is_active,
                }
                for p in peer_registry.get_all_active()
            ]
        }

    def _verify_caller(request: Request, body: bytes) -> bool:
        """Verify the request signature from a caller."""
        node_id = request.headers.get("X-Node-ID", "")
        timestamp = request.headers.get("X-Timestamp", "")
        signature = request.headers.get("X-Signature", "")

        if not all([node_id, timestamp, signature]):
            # Allow unsigned requests in development
            logger.warning("Unsigned request received — allowing in dev mode")
            return True

        return verify_request(
            public_key_hex=node_id,
            method=request.method,
            path=request.url.path,
            body=body,
            timestamp=timestamp,
            signature_hex=signature,
        )

    return app
