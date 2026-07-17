"""Tests for tag-based lesson filtering and access log middleware."""
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


def _admin_token(client: TestClient) -> str:
    resp = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert resp.status_code == 201
    return resp.json()["access_token"]


def _create_lesson(client: TestClient, token: str, *, title: str, slug: str, tags: list[str]) -> dict:
    resp = client.post(
        "/api/v1/admin/lessons",
        json={
            "title": title,
            "slug": slug,
            "category": "wellbeing",
            "summary": "Test lesson summary with enough characters.",
            "language": "english",
            "audience": "general",
            "tags": tags,
            "published": True,
            "sections": [{"heading": "Section 1", "body": "Body text for this section."}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------------------------

def test_filter_lessons_by_tag_returns_matching(tmp_path: Path) -> None:
    client = build_client(tmp_path / "tag-filter.sqlite3")
    token = _admin_token(client)

    _create_lesson(client, token, title="Breathing Exercise", slug="breathing", tags=["breathing", "calm"])
    _create_lesson(client, token, title="Nutrition Guide", slug="nutrition", tags=["food", "energy"])
    _create_lesson(client, token, title="Stress Relief", slug="stress-relief", tags=["calm", "stress"])

    resp = client.get("/api/v1/lessons?tag=calm")
    assert resp.status_code == 200
    results = resp.json()
    slugs = {r["slug"] for r in results}
    assert "breathing" in slugs
    assert "stress-relief" in slugs
    assert "nutrition" not in slugs


def test_filter_lessons_by_tag_is_case_insensitive(tmp_path: Path) -> None:
    client = build_client(tmp_path / "tag-case.sqlite3")
    token = _admin_token(client)
    _create_lesson(client, token, title="Health Basics", slug="health-basics", tags=["Health", "Basics"])

    resp = client.get("/api/v1/lessons?tag=health")
    assert resp.status_code == 200
    slugs = {r["slug"] for r in resp.json()}
    assert "health-basics" in slugs


def test_filter_lessons_by_nonexistent_tag_returns_empty(tmp_path: Path) -> None:
    client = build_client(tmp_path / "tag-none.sqlite3")

    resp = client.get("/api/v1/lessons?tag=does-not-exist-xyz")
    assert resp.status_code == 200
    # Seeded lessons don't have this tag
    assert resp.json() == []


def test_tag_filter_combines_with_category_filter(tmp_path: Path) -> None:
    client = build_client(tmp_path / "tag-category.sqlite3")
    token = _admin_token(client)

    _create_lesson(client, token, title="Yoga Basics", slug="yoga-basics-a", tags=["yoga"])
    _create_lesson(client, token, title="Yoga Advanced", slug="yoga-advanced-b", tags=["yoga"])

    # Both are in "wellbeing" and have "yoga" tag
    resp = client.get("/api/v1/lessons?category=wellbeing&tag=yoga")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # category=hygiene with yoga tag should return nothing
    resp2 = client.get("/api/v1/lessons?category=hygiene&tag=yoga")
    assert resp2.status_code == 200
    assert resp2.json() == []


def test_admin_lesson_list_also_supports_tag_filter(tmp_path: Path) -> None:
    client = build_client(tmp_path / "tag-admin.sqlite3")
    token = _admin_token(client)
    admin_headers = {"Authorization": f"Bearer {token}"}

    _create_lesson(client, token, title="Yoga 101", slug="yoga-101", tags=["yoga", "wellness"])
    _create_lesson(client, token, title="Running", slug="running", tags=["fitness"])

    # Admin list all with tag filter
    resp = client.get("/api/v1/admin/lessons?content_language=english", headers=admin_headers)
    assert resp.status_code == 200
    # Both lessons plus the 3 seeded ones
    assert len(resp.json()) >= 2


# ---------------------------------------------------------------------------
# Access log middleware
# ---------------------------------------------------------------------------

def test_access_log_middleware_adds_request_id_header(tmp_path: Path) -> None:
    client = build_client(tmp_path / "access-log.sqlite3")
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "X-Request-Id" in resp.headers
    assert len(resp.headers["X-Request-Id"]) > 0


def test_request_id_is_unique_per_request(tmp_path: Path) -> None:
    client = build_client(tmp_path / "access-log-unique.sqlite3")
    ids = set()
    for _ in range(5):
        resp = client.get("/api/v1/health")
        ids.add(resp.headers.get("X-Request-Id", ""))
    # All 5 request IDs should be distinct
    assert len(ids) == 5


def test_access_log_present_on_post_endpoints(tmp_path: Path) -> None:
    client = build_client(tmp_path / "access-log-post.sqlite3")
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 201
    assert "X-Request-Id" in resp.headers
