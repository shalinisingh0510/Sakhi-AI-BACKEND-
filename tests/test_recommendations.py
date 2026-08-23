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


def _register_and_token(client: TestClient, payload: dict) -> str:
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()["access_token"]


def _create_lesson(client: TestClient, admin_token: str, *, title: str, slug: str, category: str, language: str = "english") -> None:
    response = client.post(
        "/api/v1/admin/lessons",
        json={
            "title": title,
            "slug": slug,
            "category": category,
            "summary": f"{title} summary for recommendations.",
            "language": language,
            "audience": "general",
            "tags": [category, language],
            "published": True,
            "sections": [
                {
                    "heading": f"About {title}",
                    "body": f"Helpful guidance for {title.lower()}.",
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201


def _track_lesson_event(client: TestClient, token: str, *, event_type: str, lesson_slug: str) -> None:
    response = client.post(
        "/api/v1/analytics/events",
        json={"event_type": event_type, "metadata": {"lesson_slug": lesson_slug}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_recommendations_prefer_matching_language_when_there_is_no_progress(tmp_path: Path) -> None:
    client = build_client(tmp_path / "recommendations-language.sqlite3")
    user_token = _register_and_token(client, REGISTER_USER)
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    headers = {"Authorization": f"Bearer {user_token}"}

    _create_lesson(client, admin_token, title="Language Match", slug="language-match", category="recommendation-track", language="english")
    _create_lesson(client, admin_token, title="Language Mismatch", slug="language-mismatch", category="recommendation-track", language="hindi")

    response = client.get("/api/v1/recommendations/lessons?limit=2", headers=headers)
    assert response.status_code == 200
    recommendations = response.json()

    assert recommendations[0]["lesson"]["slug"] == "language-match"
    assert "preferred language" in recommendations[0]["reason"]


def test_recommendations_use_progress_category_and_hide_completed_lessons_by_default(tmp_path: Path) -> None:
    client = build_client(tmp_path / "recommendations-progress.sqlite3")
    user_token = _register_and_token(client, REGISTER_USER)
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    headers = {"Authorization": f"Bearer {user_token}"}

    _create_lesson(client, admin_token, title="Cycle Basics", slug="cycle-basics", category="cycle-care")
    _create_lesson(client, admin_token, title="Cycle Next Step", slug="cycle-next-step", category="cycle-care")
    _create_lesson(client, admin_token, title="Mindset Reset", slug="mindset-reset", category="mindset")

    completed_response = client.put(
        "/api/v1/progress/lessons/cycle-basics",
        json={"status": "completed"},
        headers=headers,
    )
    assert completed_response.status_code == 200

    default_response = client.get("/api/v1/recommendations/lessons?limit=3", headers=headers)
    assert default_response.status_code == 200
    default_recommendations = default_response.json()

    assert default_recommendations[0]["lesson"]["slug"] == "cycle-next-step"
    assert all(item["lesson"]["slug"] != "cycle-basics" for item in default_recommendations)

    review_response = client.get("/api/v1/recommendations/lessons?limit=3&include_completed=true", headers=headers)
    assert review_response.status_code == 200
    review_recommendations = review_response.json()

    assert any(item["lesson"]["slug"] == "cycle-basics" for item in review_recommendations)
    assert any("review" in item["reason"].lower() for item in review_recommendations if item["lesson"]["slug"] == "cycle-basics")


def test_recommendations_use_engagement_history_when_available(tmp_path: Path) -> None:
    client = build_client(tmp_path / "recommendations-engagement.sqlite3")
    user_token = _register_and_token(client, REGISTER_USER)
    admin_token = _register_and_token(client, REGISTER_ADMIN)
    headers = {"Authorization": f"Bearer {user_token}"}

    _create_lesson(client, admin_token, title="Seen First", slug="seen-first", category="cycle-care")
    _create_lesson(client, admin_token, title="Seen Second", slug="seen-second", category="cycle-care")
    _create_lesson(client, admin_token, title="Unseen Lesson", slug="unseen-lesson", category="mindset")

    _track_lesson_event(client, user_token, event_type="lesson_view", lesson_slug="seen-second")
    _track_lesson_event(client, user_token, event_type="lesson_view", lesson_slug="seen-second")
    _track_lesson_event(client, user_token, event_type="lesson_start", lesson_slug="seen-second")
    _track_lesson_event(client, user_token, event_type="lesson_view", lesson_slug="seen-first")

    response = client.get("/api/v1/recommendations/lessons?limit=3", headers=headers)
    assert response.status_code == 200
    recommendations = response.json()

    assert recommendations[0]["lesson"]["slug"] == "seen-second"
    assert "view" in recommendations[0]["reason"].lower() or "started" in recommendations[0]["reason"].lower()
