"""Dashboard API server — exposes validator state for the frontend.

Runs alongside the validator loop, serving endpoints for the
TaoForge web dashboard (stats, events, scores, DAG).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class DashboardState:
    """Shared state between the validator loop and the dashboard API.

    The validator writes events/scores here; the API reads them.
    Thread-safe via simple append-only structures.
    """

    def __init__(self) -> None:
        self.events: deque[dict] = deque(maxlen=500)
        self.scores: dict[str, dict] = {}  # agent_id -> {score, improvements, streak, ...}
        self.stats = {
            "active_agents": 0,
            "total_cycles": 0,
            "verified_improvements": 0,
            "avg_delta": 0.0,
            "uptime_start": time.time(),
        }
        self.dag_nodes: list[dict] = []
        self.reputation: dict[str, float] = {}
        self._event_id = 0
        self._subscribers: list[asyncio.Queue] = []

    def push_event(self, event_type: str, agent: str, **kwargs: Any) -> None:
        """Push a new event (called from the validator loop)."""
        self._event_id += 1
        event = {
            "id": str(self._event_id),
            "type": event_type,
            "agent": agent,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **kwargs,
        }
        self.events.appendleft(event)

        # Notify SSE subscribers
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def update_score(self, agent_id: str, score: float, improvement: float = 0.0,
                     mutation_type: str = "", streak: int = 0) -> None:
        """Update an agent's score entry."""
        entry = self.scores.get(agent_id, {
            "agent_id": agent_id,
            "name": agent_id[:12],
            "score": 0.0,
            "improvements": 0,
            "streak": 0,
            "top_mutation": "",
            "reputation": 0.0,
        })
        entry["score"] = score
        if improvement > 0:
            entry["improvements"] = entry.get("improvements", 0) + 1
        entry["streak"] = streak
        if mutation_type:
            entry["top_mutation"] = mutation_type
        self.scores[agent_id] = entry

    def update_stats(self, active_agents: int = 0, total_cycles: int = 0,
                     verified_improvements: int = 0, avg_delta: float = 0.0) -> None:
        self.stats["active_agents"] = active_agents
        self.stats["total_cycles"] = total_cycles
        self.stats["verified_improvements"] = verified_improvements
        self.stats["avg_delta"] = avg_delta

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to SSE events. Returns a queue that receives events."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)


# Global dashboard state — shared between validator and API
_dashboard_state = DashboardState()


def get_dashboard_state() -> DashboardState:
    return _dashboard_state


def create_dashboard_app(state: DashboardState | None = None) -> FastAPI:
    """Create the FastAPI app for the dashboard API."""
    ds = state or _dashboard_state

    app = FastAPI(title="TaoForge Dashboard API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "role": "dashboard"}

    @app.get("/stats")
    async def stats():
        uptime = time.time() - ds.stats.get("uptime_start", time.time())
        return {
            "active_agents": ds.stats["active_agents"],
            "total_cycles": ds.stats["total_cycles"],
            "verified_improvements": ds.stats["verified_improvements"],
            "avg_delta": round(ds.stats["avg_delta"], 4),
            "uptime_seconds": round(uptime),
        }

    @app.get("/scores")
    async def scores():
        ranked = sorted(ds.scores.values(), key=lambda x: x.get("score", 0), reverse=True)
        return {"rankings": ranked}

    @app.get("/events")
    async def events():
        return {"events": list(ds.events)[:50]}

    @app.get("/events/stream")
    async def events_stream(request: Request):
        """Server-Sent Events stream for real-time dashboard updates."""
        q = ds.subscribe()

        async def event_generator():
            try:
                # Send recent events first as a catch-up
                for event in list(ds.events)[:10]:
                    yield f"data: {json.dumps(event)}\n\n"

                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(q.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield f": keepalive\n\n"
            finally:
                ds.unsubscribe(q)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/dag")
    async def dag():
        return {"nodes": ds.dag_nodes, "size": len(ds.dag_nodes)}

    @app.get("/reputation")
    async def reputation():
        return {"agents": ds.reputation}

    return app
