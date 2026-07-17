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


def test_user_can_track_analytics_events(tmp_path: Path) -> None:
    client = build_client(tmp_path / "analytics.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    access_token = user_response.json()["access_token"]
    user_id = user_response.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {access_token}"}

    event_response = client.post(
        "/api/v1/analytics/events",
        json={
            "event_type": "lesson_view",
            "metadata": {"lesson_slug": "understanding-periods"},
        },
        headers=headers,
    )
    assert event_response.status_code == 201
    event_payload = event_response.json()
    assert event_payload["user_id"] == user_id
    assert event_payload["event_type"] == "lesson_view"
    assert event_payload["metadata"]["lesson_slug"] == "understanding-periods"

    events_list = client.get("/api/v1/analytics/events", headers=headers)
    assert events_list.status_code == 200
    events = events_list.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "lesson_view"


def test_user_can_get_engagement_metrics(tmp_path: Path) -> None:
    client = build_client(tmp_path / "engagement.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    access_token = user_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view", "metadata": {"lesson_slug": "lesson-1"}},
        headers=headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view", "metadata": {"lesson_slug": "lesson-2"}},
        headers=headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_complete", "metadata": {"lesson_slug": "lesson-1"}},
        headers=headers,
    )

    metrics_response = client.get("/api/v1/analytics/engagement", headers=headers)
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["total_events"] == 3
    assert metrics["lesson_views"] == 2
    assert metrics["lesson_completions"] == 1
    assert metrics["last_activity"] is not None


def test_admin_can_get_platform_overview(tmp_path: Path) -> None:
    client = build_client(tmp_path / "overview.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view"},
        headers=user_headers,
    )

    overview_response = client.get("/api/v1/analytics/platform/overview", headers=admin_headers)
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["total_users"] == 2
    assert overview["total_events"] == 1
    assert overview["total_lesson_views"] == 1


def test_user_cannot_access_platform_analytics(tmp_path: Path) -> None:
    client = build_client(tmp_path / "access-control.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    overview_response = client.get("/api/v1/analytics/platform/overview", headers=user_headers)
    assert overview_response.status_code == 403


def test_analytics_events_persist_across_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent-analytics.sqlite3"

    first_client = build_client(database_path)

    user_response = first_client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    first_client.post(
        "/api/v1/analytics/events",
        json={"event_type": "login"},
        headers=user_headers,
    )
    first_client.close()

    second_client = build_client(database_path)

    login_response = second_client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert login_response.status_code == 200
    restarted_token = login_response.json()["access_token"]
    restarted_headers = {"Authorization": f"Bearer {restarted_token}"}

    events_response = second_client.get("/api/v1/analytics/events", headers=restarted_headers)
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "login"


def test_event_type_filtering(tmp_path: Path) -> None:
    client = build_client(tmp_path / "filtering.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view"},
        headers=headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view"},
        headers=headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_complete"},
        headers=headers,
    )

    all_events = client.get("/api/v1/analytics/events", headers=headers)
    assert all_events.status_code == 200
    assert len(all_events.json()) == 3

    filtered_events = client.get("/api/v1/analytics/events?event_type=lesson_view", headers=headers)
    assert filtered_events.status_code == 200
    assert len(filtered_events.json()) == 2


def test_admin_can_get_event_breakdown(tmp_path: Path) -> None:
    client = build_client(tmp_path / "breakdown.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view"},
        headers=user_headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_complete"},
        headers=user_headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "conversation_start"},
        headers=user_headers,
    )

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    breakdown_response = client.get("/api/v1/analytics/platform/event-breakdown", headers=admin_headers)
    assert breakdown_response.status_code == 200
    breakdown = breakdown_response.json()
    assert len(breakdown) == 3
    event_types = {item["event_type"] for item in breakdown}
    assert "lesson_view" in event_types
    assert "lesson_complete" in event_types
    assert "conversation_start" in event_types


def test_admin_can_get_daily_activity(tmp_path: Path) -> None:
    client = build_client(tmp_path / "daily.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    for i in range(5):
        client.post(
            "/api/v1/analytics/events",
            json={"event_type": "lesson_view"},
            headers=user_headers,
        )

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    activity_response = client.get("/api/v1/analytics/platform/daily-activity", headers=admin_headers)
    assert activity_response.status_code == 200
    activity = activity_response.json()
    assert len(activity) >= 1
    assert activity[0]["event_count"] >= 5


def test_admin_can_get_top_users(tmp_path: Path) -> None:
    client = build_client(tmp_path / "top-users.sqlite3")

    first_user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert first_user_response.status_code == 201
    first_user_token = first_user_response.json()["access_token"]
    first_user_headers = {"Authorization": f"Bearer {first_user_token}"}

    second_user_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Priya Singh",
            "email": "priya.singh@sakhi.ai",
            "password": "StrongPass456!",
        },
    )
    assert second_user_response.status_code == 201
    second_user_token = second_user_response.json()["access_token"]
    second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

    for i in range(10):
        client.post(
            "/api/v1/analytics/events",
            json={"event_type": "lesson_view"},
            headers=first_user_headers,
        )

    for i in range(3):
        client.post(
            "/api/v1/analytics/events",
            json={"event_type": "lesson_view"},
            headers=second_user_headers,
        )

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    top_users_response = client.get("/api/v1/analytics/platform/top-users", headers=admin_headers)
    assert top_users_response.status_code == 200
    top_users = top_users_response.json()
    assert len(top_users) >= 1
    assert top_users[0]["total_events"] >= 10


def test_admin_can_get_full_analytics_report(tmp_path: Path) -> None:
    client = build_client(tmp_path / "report.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_view"},
        headers=user_headers,
    )
    client.post(
        "/api/v1/analytics/events",
        json={"event_type": "lesson_complete"},
        headers=user_headers,
    )

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    report_response = client.get("/api/v1/analytics/platform/report", headers=admin_headers)
    assert report_response.status_code == 200
    report = report_response.json()
    assert "overview" in report
    assert "event_breakdown" in report
    assert "daily_activity" in report
    assert "top_users_by_engagement" in report
    assert report["overview"]["total_users"] == 2
    assert report["overview"]["total_events"] == 2


def test_event_metadata_validation(tmp_path: Path) -> None:
    client = build_client(tmp_path / "metadata.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    event_response = client.post(
        "/api/v1/analytics/events",
        json={
            "event_type": "lesson_view",
            "metadata": {
                "lesson_slug": "period-basics",
                "category": "health",
                "duration_seconds": "120",
            },
        },
        headers=headers,
    )
    assert event_response.status_code == 201
    event = event_response.json()
    assert event["metadata"]["lesson_slug"] == "period-basics"
    assert event["metadata"]["category"] == "health"
    assert event["metadata"]["duration_seconds"] == "120"


def test_invalid_event_type_rejected(tmp_path: Path) -> None:
    client = build_client(tmp_path / "validation.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_token = user_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    event_response = client.post(
        "/api/v1/analytics/events",
        json={"event_type": "invalid_event", "metadata": {}},
        headers=headers,
    )
    assert event_response.status_code == 422
