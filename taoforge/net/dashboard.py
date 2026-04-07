"""Dashboard API server — exposes validator state for the frontend.

Runs alongside the validator loop, serving endpoints for the
TaoForge web dashboard (stats, events, scores, DAG).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


class SubmitPayload(BaseModel):
    agent_name: str
    model: str
    netuid: int = 1
    initial_score: float
    final_score: float
    total_improvement: float
    accepted: int
    total_cycles: int
    thought_log: list = []
    self_portrait_svg: str = ""
    subnet_history: list = []
    source: str = "external"


_BATCH_RESULTS_PATH = Path(__file__).resolve().parents[2] / "taoforge-web" / "public" / "data" / "batch-results.json"


async def _persist_submission(payload: SubmitPayload) -> None:
    """Persist a community submission to batch-results.json and optionally push to GitHub."""
    try:
        if _BATCH_RESULTS_PATH.exists():
            data = json.loads(_BATCH_RESULTS_PATH.read_text(encoding="utf-8"))
        else:
            data = {"stats": {}, "leaderboard": [], "events": [], "mutations": [], "runs": []}

        runs: list[dict] = data.get("runs", [])

        # Find existing entry by agent name (label field)
        existing_idx = next(
            (i for i, r in enumerate(runs) if r.get("label") == payload.agent_name),
            None,
        )
        new_run = {
            "label": payload.agent_name,
            "initial_score": payload.initial_score,
            "final_score": payload.final_score,
            "total_improvement": payload.total_improvement,
            "accepted": payload.accepted,
            "total_cycles": payload.total_cycles,
            "dag_depth": payload.accepted,
            "reputation": round(min(payload.final_score, 1.0), 4),
            "elapsed_s": 0,
            "thought_log": payload.thought_log,
            "self_portrait_svg": payload.self_portrait_svg,
            "netuid": payload.netuid,
            "subnet_history": payload.subnet_history,
            "model": payload.model,
            "source": payload.source,
        }

        if existing_idx is None:
            runs.append(new_run)
        elif payload.final_score > runs[existing_idx].get("final_score", 0):
            runs[existing_idx] = new_run

        data["runs"] = runs

        # Recompute leaderboard
        data["leaderboard"] = sorted(
            [
                {
                    "name": r["label"],
                    "score": r["final_score"],
                    "improvements": r["accepted"],
                    "streak": 0,
                    "initial": r["initial_score"],
                    "delta": r["total_improvement"],
                }
                for r in runs
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        # Recompute stats
        total_improvements = sum(r.get("accepted", 0) for r in runs)
        total_cycles = sum(r.get("total_cycles", 0) for r in runs)
        deltas = [r.get("total_improvement", 0) for r in runs if r.get("total_improvement", 0) > 0]
        avg_delta = round(sum(deltas) / len(deltas), 4) if deltas else 0.0
        data["stats"] = {
            "active_agents": len(runs),
            "total_cycles": total_cycles,
            "verified_improvements": total_improvements,
            "avg_delta": avg_delta,
        }

        _BATCH_RESULTS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Persisted submission for agent %s (score=%.4f)", payload.agent_name, payload.final_score)

        # Push to GitHub if token is set
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            try:
                import base64
                import urllib.request

                repo = os.environ.get("GITHUB_REPO", "taoforge/taoforge-web")
                file_path_in_repo = "public/data/batch-results.json"
                api_url = f"https://api.github.com/repos/{repo}/contents/{file_path_in_repo}"

                # Get current SHA
                req = urllib.request.Request(
                    api_url,
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                with urllib.request.urlopen(req) as resp:
                    file_info = json.loads(resp.read())
                sha = file_info.get("sha", "")

                # Push updated content
                content_b64 = base64.b64encode(
                    json.dumps(data, indent=2).encode("utf-8")
                ).decode("ascii")
                put_data = json.dumps({
                    "message": f"feat: community submission from {payload.agent_name}",
                    "content": content_b64,
                    "sha": sha,
                }).encode("utf-8")
                put_req = urllib.request.Request(
                    api_url,
                    data=put_data,
                    method="PUT",
                    headers={
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(put_req):
                    pass
                logger.info("Pushed batch-results.json to GitHub for agent %s", payload.agent_name)
            except Exception as gh_err:
                logger.warning("GitHub push failed: %s", gh_err)
    except Exception as err:
        logger.error("Failed to persist submission: %s", err)


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

    @app.post("/submit")
    async def submit(payload: SubmitPayload):
        ds.push_event(
            "agent_submitted",
            payload.agent_name,
            model=payload.model,
            netuid=payload.netuid,
            score=payload.final_score,
            improvement=payload.total_improvement,
            source=payload.source,
        )
        ds.update_score(
            agent_id=payload.agent_name,
            score=payload.final_score,
            improvement=payload.total_improvement,
            mutation_type="community",
            streak=0,
        )
        await _persist_submission(payload)
        return {"ok": True, "agent": payload.agent_name, "score": payload.final_score}

    return app
