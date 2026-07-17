"""Tests for extended notification features: mark-all-read and delete."""
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


def _setup(client: TestClient) -> tuple[str, str, str]:
    """Register a user and admin, create 3 notifications for the user.
    Returns (user_token, admin_token, user_id).
    """
    user_reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_reg.status_code == 201
    user_token = user_reg.json()["access_token"]
    user_id = user_reg.json()["user"]["id"]

    admin_reg = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_reg.status_code == 201
    admin_token = admin_reg.json()["access_token"]

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    for i in range(3):
        client.post(
            "/api/v1/admin/notifications",
            json={
                "recipient_user_id": user_id,
                "title": f"Notification {i + 1}",
                "body": f"Body of notification {i + 1}",
                "notification_type": "announcement",
            },
            headers=admin_headers,
        )
    return user_token, admin_token, user_id


# ---------------------------------------------------------------------------
# Mark all as read
# ---------------------------------------------------------------------------

def test_mark_all_notifications_as_read(tmp_path: Path) -> None:
    client = build_client(tmp_path / "mark-all.sqlite3")
    user_token, _, _ = _setup(client)
    headers = {"Authorization": f"Bearer {user_token}"}

    # All 3 are unread initially
    count = client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread_count"]
    assert count == 3

    # Mark all as read
    resp = client.post("/api/v1/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 3

    # Unread count should now be 0
    count_after = client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread_count"]
    assert count_after == 0


def test_mark_all_read_is_idempotent(tmp_path: Path) -> None:
    client = build_client(tmp_path / "mark-all-idempotent.sqlite3")
    user_token, _, _ = _setup(client)
    headers = {"Authorization": f"Bearer {user_token}"}

    # First call marks 3
    resp1 = client.post("/api/v1/notifications/read-all", headers=headers)
    assert resp1.json()["updated_count"] == 3

    # Second call marks 0 (already all read)
    resp2 = client.post("/api/v1/notifications/read-all", headers=headers)
    assert resp2.json()["updated_count"] == 0


def test_mark_all_read_does_not_affect_other_users(tmp_path: Path) -> None:
    client = build_client(tmp_path / "mark-all-isolation.sqlite3")
    user_token, admin_token, user_id = _setup(client)

    # Create a notification for admin too
    admin_reg = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_ADMIN["email"], "password": REGISTER_ADMIN["password"]},
    )
    admin_token_fresh = admin_reg.json()["access_token"]
    admin_id = admin_reg.json()["user"]["id"]
    admin_headers = {"Authorization": f"Bearer {admin_token_fresh}"}

    client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": admin_id,
            "title": "Admin note",
            "body": "For admin only",
            "notification_type": "announcement",
        },
        headers=admin_headers,
    )

    # Mark all read for the regular user
    user_headers = {"Authorization": f"Bearer {user_token}"}
    client.post("/api/v1/notifications/read-all", headers=user_headers)

    # Admin's notification should still be unread
    admin_count = client.get("/api/v1/notifications/unread-count", headers=admin_headers).json()["unread_count"]
    assert admin_count == 1


def test_mark_all_read_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "mark-all-unauth.sqlite3")
    resp = client.post("/api/v1/notifications/read-all")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Delete notification
# ---------------------------------------------------------------------------

def test_user_can_delete_own_notification(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-notif.sqlite3")
    user_token, _, _ = _setup(client)
    headers = {"Authorization": f"Bearer {user_token}"}

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    assert len(notifications) == 3

    notif_id = notifications[0]["id"]
    resp = client.delete(f"/api/v1/notifications/{notif_id}", headers=headers)
    assert resp.status_code == 204

    after = client.get("/api/v1/notifications", headers=headers).json()
    assert len(after) == 2
    assert all(n["id"] != notif_id for n in after)


def test_delete_nonexistent_notification_returns_404(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-404.sqlite3")
    user_token, _, _ = _setup(client)
    headers = {"Authorization": f"Bearer {user_token}"}

    resp = client.delete("/api/v1/notifications/does-not-exist", headers=headers)
    assert resp.status_code == 404


def test_user_cannot_delete_other_users_notification(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-isolation.sqlite3")
    user_token, admin_token, user_id = _setup(client)

    # Get first notification ID belonging to the user
    user_headers = {"Authorization": f"Bearer {user_token}"}
    notifications = client.get("/api/v1/notifications", headers=user_headers).json()
    notif_id = notifications[0]["id"]

    # Try to delete it as admin (different user)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.delete(f"/api/v1/notifications/{notif_id}", headers=admin_headers)
    assert resp.status_code == 404  # Not found for admin — ownership enforced


def test_deleted_notification_unread_count_decrements(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-count.sqlite3")
    user_token, _, _ = _setup(client)
    headers = {"Authorization": f"Bearer {user_token}"}

    # Initially 3 unread
    assert client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread_count"] == 3

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    client.delete(f"/api/v1/notifications/{notifications[0]['id']}", headers=headers)

    # Should now be 2 total, 2 unread
    remaining = client.get("/api/v1/notifications", headers=headers).json()
    assert len(remaining) == 2
    assert client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread_count"] == 2


def test_delete_notification_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-unauth.sqlite3")
    resp = client.delete("/api/v1/notifications/some-id")
    assert resp.status_code == 401
