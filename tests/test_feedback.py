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

REGISTER_SECOND_USER = {
    "name": "Priya Singh",
    "email": "priya.singh@sakhi.ai",
    "password": "StrongPass456!",
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


def test_user_can_submit_and_list_feedback_and_persist(tmp_path: Path) -> None:
    database_path = tmp_path / "feedback.sqlite3"
    client = build_client(database_path)

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    submit_response = client.post(
        "/api/v1/feedback",
        json={
            "category": "feature_request",
            "subject": "Dark mode would help",
            "message": "It would be easier to read late at night with a dark theme.",
            "rating": 5,
        },
        headers=headers,
    )
    assert submit_response.status_code == 201
    feedback = submit_response.json()
    assert feedback["category"] == "feature_request"
    assert feedback["status"] == "open"
    assert feedback["rating"] == 5

    list_response = client.get("/api/v1/feedback", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["subject"] == "Dark mode would help"

    client.close()

    restarted_client = build_client(database_path)
    login_response = restarted_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": REGISTER_USER["password"]},
    )
    assert login_response.status_code == 200
    restarted_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    persisted_response = restarted_client.get("/api/v1/feedback", headers=restarted_headers)
    assert persisted_response.status_code == 200
    assert len(persisted_response.json()) == 1


def test_feedback_is_scoped_to_owner(tmp_path: Path) -> None:
    client = build_client(tmp_path / "feedback-scope.sqlite3")

    user_one = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_one.status_code == 201
    user_one_headers = {"Authorization": f"Bearer {user_one.json()['access_token']}"}

    user_two = client.post("/api/v1/auth/register", json=REGISTER_SECOND_USER)
    assert user_two.status_code == 201
    user_two_headers = {"Authorization": f"Bearer {user_two.json()['access_token']}"}

    client.post(
        "/api/v1/feedback",
        json={
            "category": "bug",
            "subject": "Search feels slow",
            "message": "The lesson search results take too long to load on my phone.",
        },
        headers=user_one_headers,
    )

    user_one_items = client.get("/api/v1/feedback", headers=user_one_headers)
    assert user_one_items.status_code == 200
    assert len(user_one_items.json()) == 1

    user_two_items = client.get("/api/v1/feedback", headers=user_two_headers)
    assert user_two_items.status_code == 200
    assert user_two_items.json() == []


def test_admin_can_list_and_update_feedback_status(tmp_path: Path) -> None:
    client = build_client(tmp_path / "feedback-admin.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_headers = {"Authorization": f"Bearer {user_response.json()['access_token']}"}

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_headers = {"Authorization": f"Bearer {admin_response.json()['access_token']}"}

    submit_response = client.post(
        "/api/v1/feedback",
        json={
            "category": "content_issue",
            "subject": "Lesson typo",
            "message": "There is a spelling mistake in the body hygiene lesson.",
        },
        headers=user_headers,
    )
    assert submit_response.status_code == 201
    feedback_id = submit_response.json()["id"]

    admin_list = client.get("/api/v1/admin/feedback", headers=admin_headers)
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1

    update_response = client.patch(
        f"/api/v1/admin/feedback/{feedback_id}/status",
        json={"status": "resolved", "admin_notes": "Fixed in the next content update."},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "resolved"
    assert updated["admin_notes"] == "Fixed in the next content update."
    assert updated["resolved_at"] is not None


def test_admin_stats_include_feedback_overview(tmp_path: Path) -> None:
    client = build_client(tmp_path / "feedback-stats.sqlite3")

    user_one = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_one.status_code == 201
    user_one_headers = {"Authorization": f"Bearer {user_one.json()['access_token']}"}

    user_two = client.post("/api/v1/auth/register", json=REGISTER_SECOND_USER)
    assert user_two.status_code == 201
    user_two_headers = {"Authorization": f"Bearer {user_two.json()['access_token']}"}

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_headers = {"Authorization": f"Bearer {admin_response.json()['access_token']}"}

    first_feedback = client.post(
        "/api/v1/feedback",
        json={
            "category": "general",
            "subject": "Great platform",
            "message": "The lessons are easy to follow and feel supportive.",
            "rating": 4,
        },
        headers=user_one_headers,
    )
    assert first_feedback.status_code == 201
    first_id = first_feedback.json()["id"]

    second_feedback = client.post(
        "/api/v1/feedback",
        json={
            "category": "feature_request",
            "subject": "Need voice support",
            "message": "A voice assistant would help users who cannot type easily.",
            "rating": 2,
        },
        headers=user_two_headers,
    )
    assert second_feedback.status_code == 201

    client.patch(
        f"/api/v1/admin/feedback/{first_id}/status",
        json={"status": "resolved"},
        headers=admin_headers,
    )

    stats_response = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_response.status_code == 200
    feedback = stats_response.json()["feedback"]
    assert feedback["total_feedback"] == 2
    assert feedback["open_feedback"] == 1
    assert feedback["resolved_feedback"] == 1
    assert feedback["average_rating"] == 3.0


def test_feedback_validation_rejects_invalid_category(tmp_path: Path) -> None:
    client = build_client(tmp_path / "feedback-validation.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    headers = {"Authorization": f"Bearer {register_response.json()['access_token']}"}

    response = client.post(
        "/api/v1/feedback",
        json={
            "category": "not-real",
            "subject": "Broken category",
            "message": "This should fail validation.",
        },
        headers=headers,
    )
    assert response.status_code == 422
