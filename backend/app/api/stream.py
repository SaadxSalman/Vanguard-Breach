"""WebSocket live-stream of run events."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..events import BUS

router = APIRouter()


@router.websocket("/ws/runs/{run_id}")
async def run_stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    queue = BUS.subscribe(run_id)
    await websocket.send_json({"level": "info", "node": "ws", "agent": "stream",
                               "message": f"subscribed to run {run_id}", "data": {}})
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                await websocket.send_json(payload)
            except asyncio.TimeoutError:
                await websocket.send_json({"level": "ping", "node": "ws", "agent": "stream",
                                           "message": "keepalive", "data": {}})
    except WebSocketDisconnect:
        pass
    finally:
        BUS.unsubscribe(run_id, queue)
