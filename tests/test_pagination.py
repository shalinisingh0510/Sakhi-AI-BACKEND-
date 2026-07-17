"""Tests for pagination on list endpoints."""
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

REGISTER_ADMIN = {
    "name": "Admin User",
    "email": "admin@sakhi.ai",
    "password": "AdminPass123!",
    "role": "admin",
}


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


def _register_and_token(client: TestClient, user: dict) -> str:
    resp = client.post("/api/v1/auth/register", json=user)
    assert resp.status_code == 201
    return resp.json()["access_token"]


# ------------------------------------------------------------------
# Conversation pagination
# ------------------------------------------------------------------

def test_conversations_default_pagination(tmp_path: Path) -> None:
    client = build_client(tmp_path / "conv-page.sqlite3")
    token = _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {token}"}

    # Create 5 conversations
    for i in range(5):
        client.post(
            "/api/v1/conversations",
            json={"initial_message": f"Question {i}"},
            headers=headers,
        )

    # Default page 1, page_size 20 — all 5 returned
    resp = client.get("/api/v1/conversations", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_conversations_page_size_limits(tmp_path: Path) -> None:
    client = build_client(tmp_path / "conv-page2.sqlite3")
    token = _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        client.post(
            "/api/v1/conversations",
            json={"initial_message": f"Question {i}"},
            headers=headers,
        )

    # page_size=2 — only 2 returned
    resp = client.get("/api/v1/conversations?page_size=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # page=2, page_size=2 — next 2
    resp2 = client.get("/api/v1/conversations?page=2&page_size=2", headers=headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2

    # page=3, page_size=2 — remaining 1
    resp3 = client.get("/api/v1/conversations?page=3&page_size=2", headers=headers)
    assert resp3.status_code == 200
    assert len(resp3.json()) == 1

    # page=4, page_size=2 — empty
    resp4 = client.get("/api/v1/conversations?page=4&page_size=2", headers=headers)
    assert resp4.status_code == 200
    assert len(resp4.json()) == 0


def test_conversations_pagination_pages_are_non_overlapping(tmp_path: Path) -> None:
    client = build_client(tmp_path / "conv-nooverlap.sqlite3")
    token = _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(6):
        client.post(
            "/api/v1/conversations",
            json={"initial_message": f"Unique question {i}"},
            headers=headers,
        )

    page1 = {c["id"] for c in client.get("/api/v1/conversations?page=1&page_size=3", headers=headers).json()}
    page2 = {c["id"] for c in client.get("/api/v1/conversations?page=2&page_size=3", headers=headers).json()}
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1.isdisjoint(page2)


# ------------------------------------------------------------------
# Notification pagination
# ------------------------------------------------------------------

def test_notifications_pagination(tmp_path: Path) -> None:
    client = build_client(tmp_path / "notif-page.sqlite3")
    token = _register_and_token(client, REGISTER_USER)
    user_id = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()["id"]
    headers = {"Authorization": f"Bearer {token}"}

    admin_token = _register_and_token(client, REGISTER_ADMIN)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create 7 notifications for the user
    for i in range(7):
        client.post(
            "/api/v1/admin/notifications",
            json={
                "recipient_user_id": user_id,
                "title": f"Notification {i}",
                "body": f"Body {i}",
                "notification_type": "announcement",
            },
            headers=admin_headers,
        )

    # Default page — all 7
    resp = client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 7

    # page_size=3
    resp2 = client.get("/api/v1/notifications?page_size=3", headers=headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 3

    # page=3, page_size=3 — last 1
    resp3 = client.get("/api/v1/notifications?page=3&page_size=3", headers=headers)
    assert resp3.status_code == 200
    assert len(resp3.json()) == 1


def test_pagination_invalid_params_rejected(tmp_path: Path) -> None:
    client = build_client(tmp_path / "page-invalid.sqlite3")
    token = _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {token}"}

    # page=0 is invalid (ge=1)
    resp = client.get("/api/v1/conversations?page=0", headers=headers)
    assert resp.status_code == 422

    # page_size=0 is invalid
    resp2 = client.get("/api/v1/conversations?page_size=0", headers=headers)
    assert resp2.status_code == 422

    # page_size > 100 is invalid
    resp3 = client.get("/api/v1/conversations?page_size=101", headers=headers)
    assert resp3.status_code == 422
