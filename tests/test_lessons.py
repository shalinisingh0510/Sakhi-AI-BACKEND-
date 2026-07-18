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


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


def test_public_lesson_catalog_exposes_seeded_content(tmp_path: Path) -> None:
    client = build_client(tmp_path / "seeded-lessons.sqlite3")

    lessons_response = client.get("/api/v1/lessons")
    assert lessons_response.status_code == 200
    lessons = lessons_response.json()
    assert len(lessons) >= 3
    assert any(lesson["slug"] == "understanding-periods" for lesson in lessons)

    categories_response = client.get("/api/v1/lessons/categories")
    assert categories_response.status_code == 200
    categories = {entry["name"] for entry in categories_response.json()}
    assert "menstrual-health" in categories



def test_public_lesson_search_finds_new_content(tmp_path: Path) -> None:
    client = build_client(tmp_path / "search-lessons.sqlite3")

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]

    create_response = client.post(
        "/api/v1/admin/lessons",
        json={
            "title": "Evening Wind-Down",
            "slug": "evening-wind-down",
            "category": "wellbeing",
            "summary": "A short routine for calmer evenings.",
            "language": "english",
            "audience": "general",
            "tags": ["sleep", "calm"],
            "published": True,
            "sections": [
                {
                    "heading": "Quiet pause",
                    "body": "A moonstone moment can help the body settle before sleep.",
                },
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201

    search_response = client.get("/api/v1/lessons?search=moonstone")
    assert search_response.status_code == 200
    results = search_response.json()
    assert any(lesson["slug"] == "evening-wind-down" for lesson in results)


def test_lesson_can_return_localized_content_and_fallback(tmp_path: Path) -> None:
    client = build_client(tmp_path / "localized-lessons.sqlite3")

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]

    create_response = client.post(
        "/api/v1/admin/lessons",
        json={
            "title": "Mindful Breathing",
            "slug": "mindful-breathing",
            "category": "wellbeing",
            "summary": "A short practice for calming the body and settling attention.",
            "language": "english",
            "audience": "general",
            "tags": ["breathing", "calm"],
            "published": True,
            "sections": [
                {"heading": "Start slowly", "body": "Breathe in gently through your nose and let the air out slowly."},
            ],
            "translations": [
                {
                    "language": "hindi",
                    "title": "???? ?????",
                    "summary": "???? ?? ???? ???? ?? ??? ???? ???? ???? ?? ???? ???????",
                    "sections": [
                        {
                            "heading": "???? ???? ????",
                            "body": "??? ?? ???? ???? ??? ?? ??? ????-???? ???? ????",
                        }
                    ],
                }
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201

    localized_detail_response = client.get("/api/v1/lessons/mindful-breathing?content_language=hindi")
    assert localized_detail_response.status_code == 200
    localized_detail = localized_detail_response.json()
    assert localized_detail["language"] == "hindi"
    assert localized_detail["title"] == "???? ?????"
    assert localized_detail["sections"][0]["heading"] == "???? ???? ????"
    assert set(localized_detail["available_languages"]) == {"english", "hindi"}

    fallback_detail_response = client.get("/api/v1/lessons/mindful-breathing?content_language=marathi")
    assert fallback_detail_response.status_code == 200
    fallback_detail = fallback_detail_response.json()
    assert fallback_detail["language"] == "english"
    assert fallback_detail["title"] == "Mindful Breathing"

    localized_catalog_response = client.get("/api/v1/lessons?content_language=hindi")
    assert localized_catalog_response.status_code == 200
    localized_catalog = localized_catalog_response.json()
    assert any(lesson["slug"] == "mindful-breathing" and lesson["title"] == "???? ?????" for lesson in localized_catalog)


def test_admin_can_create_update_and_delete_lesson(tmp_path: Path) -> None:
    client = build_client(tmp_path / "lesson-crud.sqlite3")

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]

    create_response = client.post(
        "/api/v1/admin/lessons",
        json={
            "title": "Nutrition Basics",
            "slug": "nutrition-basics",
            "category": "nutrition",
            "summary": "Simple food guidance for energy and balance.",
            "language": "english",
            "audience": "general",
            "tags": ["food", "energy"],
            "published": True,
            "sections": [
                {"heading": "Balanced meals", "body": "Include grains, protein, fruits, vegetables, and water."},
                {"heading": "Helpful habit", "body": "Small regular meals can help some people feel more steady during the day."},
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created_lesson = create_response.json()
    lesson_id = created_lesson["id"]
    assert created_lesson["slug"] == "nutrition-basics"
    assert created_lesson["section_count"] == 2

    public_detail_response = client.get("/api/v1/lessons/nutrition-basics")
    assert public_detail_response.status_code == 200
    assert public_detail_response.json()["title"] == "Nutrition Basics"

    update_response = client.patch(
        f"/api/v1/admin/lessons/{lesson_id}",
        json={"published": False, "title": "Nutrition Basics Updated"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Nutrition Basics Updated"
    assert update_response.json()["published"] is False

    public_after_unpublish = client.get("/api/v1/lessons/nutrition-basics")
    assert public_after_unpublish.status_code == 404

    admin_lessons_response = client.get(
        "/api/v1/admin/lessons",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_lessons_response.status_code == 200
    assert any(lesson["slug"] == "nutrition-basics" for lesson in admin_lessons_response.json())

    delete_response = client.delete(
        f"/api/v1/admin/lessons/{lesson_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204

    after_delete_response = client.get(
        f"/api/v1/admin/lessons/{lesson_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert after_delete_response.status_code == 404


def test_lesson_persists_across_app_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "persisted-lessons.sqlite3"
    client_one = build_client(database_path)

    admin_response = client_one.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]

    create_response = client_one.post(
        "/api/v1/admin/lessons",
        json={
            "title": "Sleep and Rest",
            "slug": "sleep-and-rest",
            "category": "wellbeing",
            "summary": "Why rest matters and how to build a steady bedtime habit.",
            "language": "english",
            "audience": "general",
            "tags": ["sleep", "rest"],
            "sections": [
                {"heading": "Why rest matters", "body": "Sleep helps the brain and body recover."},
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    client_one.close()

    client_two = build_client(database_path)
    public_response = client_two.get("/api/v1/lessons/sleep-and-rest")
    assert public_response.status_code == 200
    assert public_response.json()["slug"] == "sleep-and-rest"
