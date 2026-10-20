"""Run-scoped event bus: persists telemetry and fans it out to WebSocket clients."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import db

log = logging.getLogger("vanguard.events")


class EventBus:
    """In-process pub/sub keyed by run_id, with durable copy in SQLite."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def publish_sync(self, run_id: str, level: str, node: str, agent: str,
                     message: str, data: dict[str, Any] | None = None) -> None:
        """Thread-safe publisher usable from synchronous agent code."""
        data = data or {}
        try:
            db.insert("events", {
                "run_id": run_id, "ts": db.now(), "level": level, "node": node,
                "agent": agent, "message": message, "data": db.dumps(data),
            })
        except Exception as exc:  # pragma: no cover - telemetry must never break a run
            log.warning("event persist failed: %s", exc)
        payload = {"level": level, "node": node, "agent": agent,
                   "message": message, "data": data}
        for queue in list(self._subscribers.get(run_id, ())):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def publish(self, run_id: str, level: str, node: str, agent: str,
                      message: str, data: dict[str, Any] | None = None) -> None:
        self.publish_sync(run_id, level, node, agent, message, data)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.setdefault(run_id, set()).add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(run_id)
        if subs:
            subs.discard(queue)
            if not subs:
                self._subscribers.pop(run_id, None)


BUS = EventBus()
