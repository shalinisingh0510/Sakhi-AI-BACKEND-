"""
WebSocket connection manager for real-time notifications.

Each authenticated user can maintain a persistent WebSocket connection.
When a new notification is created for that user the notification service
calls `ws_manager.send_notification(user_id, payload)` and the message is
delivered instantly without polling.

Usage (server-side push):
    from app.core.websocket_manager import ws_manager
    await ws_manager.send_notification(user_id, {"type": "notification", ...})
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Thread-safe mapping from user_id → set of active WebSocket connections."""

    def __init__(self) -> None:
        # user_id -> set of connected websockets
        self._connections: defaultdict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.info("WebSocket connected: user_id=%s total=%d", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]
        logger.info("WebSocket disconnected: user_id=%s", user_id)

    async def send_notification(self, user_id: str, payload: dict) -> None:
        """Push a JSON payload to all connections belonging to user_id."""
        sockets = list(self._connections.get(user_id, set()))
        if not sockets:
            return
        message = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast(self, payload: dict) -> None:
        """Push a JSON payload to every connected user."""
        user_ids = list(self._connections.keys())
        await asyncio.gather(
            *(self.send_notification(uid, payload) for uid in user_ids),
            return_exceptions=True,
        )

    @property
    def connected_user_ids(self) -> list[str]:
        return list(self._connections.keys())


# Singleton shared across the whole process
ws_manager = WebSocketManager()
