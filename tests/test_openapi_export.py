from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_versioned_openapi_export_returns_schema() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == 'attachment; filename="sakhi-ai-openapi.json"'

    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert payload["info"]["title"] == "Sakhi AI API"
    assert "/api/v1/auth/login" in payload["paths"]
    assert "/api/v1/lessons" in payload["paths"]
