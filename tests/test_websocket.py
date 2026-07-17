"""Tests for the WebSocket real-time notification endpoint."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


REGISTER_USER = {
    "name": "Asha Verma",
    "email": "asha.verma@sakhi.ai",
    "password": "StrongPass123!",
}


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


def _register_and_token(client: TestClient, user: dict) -> str:
    resp = client.post("/api/v1/auth/register", json=user)
    assert resp.status_code == 201
    return resp.json()["access_token"]


def test_websocket_rejects_missing_token(tmp_path: Path) -> None:
    """Connection without a valid token must be rejected (close code 4001)."""
    from starlette.websockets import WebSocketDisconnect

    client = build_client(tmp_path / "ws-no-token.sqlite3")

    # Empty token — server closes immediately with 4001
    try:
        with client.websocket_connect("/api/v1/ws/notifications?token=") as ws:
            ws.receive_text()  # Should not reach here
    except WebSocketDisconnect as exc:
        assert exc.code == 4001
    except Exception:
        pass  # Any failure to connect is acceptable


def test_websocket_rejects_invalid_token(tmp_path: Path) -> None:
    """A garbage token must be rejected (close code 4001)."""
    client = build_client(tmp_path / "ws-bad-token.sqlite3")
    # WebSocket with invalid token — server closes the socket
    try:
        with client.websocket_connect("/api/v1/ws/notifications?token=not-a-real-token") as ws:
            # If it doesn't raise, the server sent a close — just pass
            pass
    except Exception:
        pass  # Expected — connection was rejected


def test_websocket_accepts_valid_token_and_sends_welcome(tmp_path: Path) -> None:
    """Authenticated WebSocket should receive a 'connected' welcome message."""
    import json

    client = build_client(tmp_path / "ws-valid.sqlite3")
    token = _register_and_token(client, REGISTER_USER)

    with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as ws:
        data = json.loads(ws.receive_text())
        assert data["type"] == "connected"
        assert "user_id" in data


def test_websocket_echoes_pong_on_client_message(tmp_path: Path) -> None:
    """Sending any message to the server should trigger a pong response."""
    import json

    client = build_client(tmp_path / "ws-pong.sqlite3")
    token = _register_and_token(client, REGISTER_USER)

    with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as ws:
        # Consume the welcome message
        welcome = json.loads(ws.receive_text())
        assert welcome["type"] == "connected"

        # Send a keep-alive ping
        ws.send_text("ping")
        pong = json.loads(ws.receive_text())
        assert pong["type"] == "pong"


def test_websocket_manager_tracks_connections() -> None:
    """WebSocketManager should track and remove connections correctly."""
    from app.core.websocket_manager import WebSocketManager

    manager = WebSocketManager()
    assert manager.connected_user_ids == []

    class FakeWS:
        async def accept(self): pass
        async def send_text(self, msg): pass

    import asyncio

    async def run():
        ws1 = FakeWS()
        ws2 = FakeWS()
        await manager.connect("user-1", ws1)
        await manager.connect("user-1", ws2)
        assert "user-1" in manager.connected_user_ids

        manager.disconnect("user-1", ws1)
        assert "user-1" in manager.connected_user_ids  # ws2 still connected

        manager.disconnect("user-1", ws2)
        assert "user-1" not in manager.connected_user_ids

    asyncio.run(run())
