"""
WebSocket endpoint for real-time notifications.

Clients authenticate by passing their access token as a query parameter:

    ws://host/api/v1/ws/notifications?token=<access_token>

Once connected the client will receive JSON messages whenever a new notification
is created for their account.  The payload format is:

    {
        "type": "notification",
        "data": { <NotificationItem fields> }
    }

The server sends a heartbeat ping every 30 seconds so the connection stays alive
through proxies and firewalls.  The client can send any message to keep the
connection open; the server will echo {"type": "pong"} back.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_HEARTBEAT_INTERVAL = 30  # seconds


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Access token for authentication"),
) -> None:
    """
    Establish a real-time notification stream for the authenticated user.

    Query parameters:
        token: A valid access token obtained from POST /api/v1/auth/login or /register.
    """
    # Resolve the user from the token before accepting the connection
    auth_service = websocket.app.state.auth_service
    try:
        from app.services.auth import InvalidTokenError

        user = auth_service.resolve_current_user(access_token=token)
    except Exception:
        # Reject the connection with 4001 (policy violation / auth failure)
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user.id, websocket)
    try:
        # Send a welcome message so the client knows it is connected
        await websocket.send_text(
            json.dumps({"type": "connected", "user_id": user.id})
        )

        # Keep the connection alive with periodic heartbeats
        while True:
            try:
                # Wait for a client message with a timeout equal to heartbeat interval
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=_HEARTBEAT_INTERVAL,
                )
                # Echo a pong for any client ping/keep-alive message
                await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # No client message — send a server-side ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user.id, websocket)
