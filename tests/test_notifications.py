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

REGISTER_SECOND_USER = {
    "name": "Priya Singh",
    "email": "priya.singh@sakhi.ai",
    "password": "StrongPass456!",
}


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


def test_user_can_list_notifications_and_mark_as_read(tmp_path: Path) -> None:
    client = build_client(tmp_path / "notifications.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    access_token = user_response.json()["access_token"]
    user_id = user_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {access_token}"}

    empty_list_response = client.get("/api/v1/notifications", headers=headers)
    assert empty_list_response.status_code == 200
    assert empty_list_response.json() == []

    unread_count_response = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_count_response.status_code == 200
    assert unread_count_response.json()["unread_count"] == 0

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_notification_response = client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": user_id,
            "title": "Welcome to Sakhi AI",
            "body": "Thank you for joining our platform!",
            "notification_type": "announcement",
            "metadata": {"source": "admin"},
        },
        headers=admin_headers,
    )
    assert create_notification_response.status_code == 201
    create_payload = create_notification_response.json()
    assert create_payload["created_count"] == 1
    assert len(create_payload["notifications"]) == 1

    list_response = client.get("/api/v1/notifications", headers=headers)
    assert list_response.status_code == 200
    notifications = list_response.json()
    assert len(notifications) == 1
    assert notifications[0]["title"] == "Welcome to Sakhi AI"
    assert notifications[0]["is_read"] is False

    unread_count_after = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_count_after.status_code == 200
    assert unread_count_after.json()["unread_count"] == 1

    notification_id = notifications[0]["id"]
    mark_read_response = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )
    assert mark_read_response.status_code == 200
    mark_read_payload = mark_read_response.json()
    assert mark_read_payload["is_read"] is True
    assert mark_read_payload["read_at"] is not None

    unread_count_after_read = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_count_after_read.status_code == 200
    assert unread_count_after_read.json()["unread_count"] == 0


def test_admin_can_create_notification_for_all_users(tmp_path: Path) -> None:
    client = build_client(tmp_path / "broadcast.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]

    second_user_response = client.post("/api/v1/auth/register", json=REGISTER_SECOND_USER)
    assert second_user_response.status_code == 201
    second_user_id = second_user_response.json()["user"]["id"]

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    broadcast_response = client.post(
        "/api/v1/admin/notifications",
        json={
            "title": "System Maintenance",
            "body": "We will be performing maintenance tonight.",
            "notification_type": "system",
        },
        headers=admin_headers,
    )
    assert broadcast_response.status_code == 201
    broadcast_payload = broadcast_response.json()
    assert broadcast_payload["created_count"] == 3

    user_login = client.post("/api/v1/auth/login", json=REGISTER_USER)
    user_token = user_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    user_notifications = client.get("/api/v1/notifications", headers=user_headers)
    assert user_notifications.status_code == 200
    assert len(user_notifications.json()) == 1
    assert user_notifications.json()[0]["title"] == "System Maintenance"

    second_user_login = client.post("/api/v1/auth/login", json=REGISTER_SECOND_USER)
    second_user_token = second_user_login.json()["access_token"]
    second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

    second_user_notifications = client.get("/api/v1/notifications", headers=second_user_headers)
    assert second_user_notifications.status_code == 200
    assert len(second_user_notifications.json()) == 1
    assert second_user_notifications.json()[0]["title"] == "System Maintenance"


def test_notifications_persist_across_app_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent-notifications.sqlite3"

    first_client = build_client(database_path)

    user_response = first_client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    admin_response = first_client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_notification_response = first_client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": user_id,
            "title": "Persistent Notification",
            "body": "This should persist across restarts",
            "notification_type": "reminder",
        },
        headers=admin_headers,
    )
    assert create_notification_response.status_code == 201

    first_client.close()

    second_client = build_client(database_path)

    login_response = second_client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert login_response.status_code == 200
    restarted_token = login_response.json()["access_token"]
    restarted_headers = {"Authorization": f"Bearer {restarted_token}"}

    persisted_notifications = second_client.get("/api/v1/notifications", headers=restarted_headers)
    assert persisted_notifications.status_code == 200
    assert len(persisted_notifications.json()) == 1
    assert persisted_notifications.json()[0]["title"] == "Persistent Notification"


def test_user_cannot_access_other_users_notifications(tmp_path: Path) -> None:
    client = build_client(tmp_path / "isolation.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    second_user_response = client.post("/api/v1/auth/register", json=REGISTER_SECOND_USER)
    assert second_user_response.status_code == 201
    second_user_token = second_user_response.json()["access_token"]
    second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_notification_response = client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": user_id,
            "title": "Private Notification",
            "body": "This is only for the first user",
            "notification_type": "announcement",
        },
        headers=admin_headers,
    )
    assert create_notification_response.status_code == 201
    notification_id = create_notification_response.json()["notifications"][0]["id"]

    first_user_notifications = client.get("/api/v1/notifications", headers=user_headers)
    assert first_user_notifications.status_code == 200
    assert len(first_user_notifications.json()) == 1

    second_user_notifications = client.get("/api/v1/notifications", headers=second_user_headers)
    assert second_user_notifications.status_code == 200
    assert len(second_user_notifications.json()) == 0

    mark_read_response = client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=second_user_headers,
    )
    assert mark_read_response.status_code == 404


def test_lesson_completion_creates_notification(tmp_path: Path) -> None:
    client = build_client(tmp_path / "lesson-notification.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    progress_response = client.put(
        "/api/v1/progress/lessons/understanding-periods",
        json={"status": "completed"},
        headers=user_headers,
    )
    assert progress_response.status_code == 200

    notifications_response = client.get("/api/v1/notifications", headers=user_headers)
    assert notifications_response.status_code == 200
    notifications = notifications_response.json()
    assert len(notifications) == 1
    assert notifications[0]["notification_type"] == "lesson_completed"
    assert "Understanding Periods" in notifications[0]["title"]
    assert notifications[0]["metadata"]["lesson_slug"] == "understanding-periods"


def test_admin_cannot_create_notification_for_nonexistent_user(tmp_path: Path) -> None:
    client = build_client(tmp_path / "invalid-user.sqlite3")

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_notification_response = client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": "nonexistent-user-id",
            "title": "Test Notification",
            "body": "This should fail",
            "notification_type": "announcement",
        },
        headers=admin_headers,
    )
    assert create_notification_response.status_code == 404


def test_notification_metadata_validation(tmp_path: Path) -> None:
    client = build_client(tmp_path / "metadata-validation.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_notification_response = client.post(
        "/api/v1/admin/notifications",
        json={
            "recipient_user_id": user_id,
            "title": "Metadata Test",
            "body": "Testing metadata handling",
            "notification_type": "reminder",
            "metadata": {
                "priority": "high",
                "category": "health",
                "action_url": "/lessons/period-basics",
            },
        },
        headers=admin_headers,
    )
    assert create_notification_response.status_code == 201
    notification = create_notification_response.json()["notifications"][0]
    assert notification["metadata"]["priority"] == "high"
    assert notification["metadata"]["category"] == "health"
    assert notification["metadata"]["action_url"] == "/lessons/period-basics"


def test_unread_only_filtering(tmp_path: Path) -> None:
    client = build_client(tmp_path / "unread-filter.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    for i in range(3):
        client.post(
            "/api/v1/admin/notifications",
            json={
                "recipient_user_id": user_id,
                "title": f"Notification {i+1}",
                "body": f"Body {i+1}",
                "notification_type": "announcement",
            },
            headers=admin_headers,
        )

    all_notifications = client.get("/api/v1/notifications", headers=user_headers)
    assert all_notifications.status_code == 200
    assert len(all_notifications.json()) == 3

    notification_id = all_notifications.json()[0]["id"]
    client.patch(f"/api/v1/notifications/{notification_id}/read", headers=user_headers)

    all_notifications_after = client.get("/api/v1/notifications", headers=user_headers)
    assert all_notifications_after.status_code == 200
    assert len(all_notifications_after.json()) == 3

    unread_count = client.get("/api/v1/notifications/unread-count", headers=user_headers)
    assert unread_count.json()["unread_count"] == 2
