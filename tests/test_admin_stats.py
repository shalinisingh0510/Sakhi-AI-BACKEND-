"""Tests for admin dashboard stats and enhanced health check."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

REGISTER_ADMIN = {
    "name": "Admin User",
    "email": "admin@sakhi.ai",
    "password": "AdminPass123!",
    "role": "admin",
}

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


# ------------------------------------------------------------------
# Enhanced health check
# ------------------------------------------------------------------

def test_health_check_includes_database_status(tmp_path: Path) -> None:
    client = build_client(tmp_path / "health-db.sqlite3")
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["service"] == "Sakhi AI API"
    assert "version" in payload
    assert "environment" in payload


def test_health_check_returns_all_required_fields(tmp_path: Path) -> None:
    client = build_client(tmp_path / "health-fields.sqlite3")
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    payload = resp.json()
    for field in ("status", "service", "version", "environment", "database"):
        assert field in payload, f"Missing field: {field}"


# ------------------------------------------------------------------
# Admin stats dashboard
# ------------------------------------------------------------------

def test_admin_stats_returns_correct_structure(tmp_path: Path) -> None:
    client = build_client(tmp_path / "admin-stats.sqlite3")
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "users" in data
    assert "lessons" in data
    assert "engagement" in data

    assert "total" in data["users"]
    assert "active_last_7_days" in data["users"]
    assert "active_last_30_days" in data["users"]

    assert "total" in data["lessons"]
    assert "published" in data["lessons"]
    assert "unpublished" in data["lessons"]
    assert "categories" in data["lessons"]

    assert "total_events" in data["engagement"]
    assert "total_lesson_views" in data["engagement"]
    assert "total_lesson_completions" in data["engagement"]
    assert "total_conversations" in data["engagement"]
    assert "total_messages" in data["engagement"]


def test_admin_stats_user_count_is_accurate(tmp_path: Path) -> None:
    client = build_client(tmp_path / "stats-users.sqlite3")
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["users"]["total"] == 2


def test_admin_stats_lesson_counts_reflect_seeded_content(tmp_path: Path) -> None:
    client = build_client(tmp_path / "stats-lessons.sqlite3")
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 200
    lessons = resp.json()["lessons"]
    # 3 seeded lessons are published
    assert lessons["published"] >= 3
    assert lessons["unpublished"] == 0
    assert lessons["categories"] >= 3


def test_admin_stats_engagement_increments_with_events(tmp_path: Path) -> None:
    client = build_client(tmp_path / "stats-events.sqlite3")
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    user_token = _register_and_token(client, REGISTER_USER)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Track some events
    for _ in range(3):
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

    resp = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    engagement = resp.json()["engagement"]
    assert engagement["total_events"] == 4
    assert engagement["total_lesson_views"] == 3
    assert engagement["total_lesson_completions"] == 1


def test_admin_stats_requires_admin_role(tmp_path: Path) -> None:
    client = build_client(tmp_path / "stats-rbac.sqlite3")
    user_token = _register_and_token(client, REGISTER_USER)
    headers = {"Authorization": f"Bearer {user_token}"}

    resp = client.get("/api/v1/admin/stats", headers=headers)
    assert resp.status_code == 403


def test_admin_stats_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "stats-unauth.sqlite3")
    resp = client.get("/api/v1/admin/stats")
    assert resp.status_code == 401
