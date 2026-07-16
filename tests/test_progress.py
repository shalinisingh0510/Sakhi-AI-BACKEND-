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


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


def test_user_can_track_progress_and_resume_after_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "progress.sqlite3"
    client = build_client(database_path)

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    empty_list_response = client.get("/api/v1/progress", headers=headers)
    assert empty_list_response.status_code == 200
    assert empty_list_response.json() == []

    empty_summary_response = client.get("/api/v1/progress/summary", headers=headers)
    assert empty_summary_response.status_code == 200
    assert empty_summary_response.json() == {
        "total_lessons": 0,
        "completed_lessons": 0,
        "in_progress_lessons": 0,
        "not_started_lessons": 0,
        "completion_rate": 0.0,
        "average_progress_percent": 0.0,
    }

    progress_response = client.put(
        "/api/v1/progress/lessons/understanding-periods",
        json={
            "status": "in_progress",
            "progress_percent": 40,
            "notes": "Reviewed the first section",
        },
        headers=headers,
    )
    assert progress_response.status_code == 200
    progress_payload = progress_response.json()
    assert progress_payload["lesson"]["slug"] == "understanding-periods"
    assert progress_payload["status"] == "in_progress"
    assert progress_payload["progress_percent"] == 40
    assert progress_payload["notes"] == "Reviewed the first section"

    get_progress_response = client.get(
        "/api/v1/progress/lessons/understanding-periods",
        headers=headers,
    )
    assert get_progress_response.status_code == 200
    assert get_progress_response.json()["lesson"]["title"] == "Understanding Periods"

    complete_response = client.put(
        "/api/v1/progress/lessons/understanding-periods",
        json={"status": "completed"},
        headers=headers,
    )
    assert complete_response.status_code == 200
    completed_payload = complete_response.json()
    assert completed_payload["status"] == "completed"
    assert completed_payload["progress_percent"] == 100
    assert completed_payload["completed_at"] is not None

    summary_response = client.get("/api/v1/progress/summary", headers=headers)
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["total_lessons"] == 1
    assert summary_payload["completed_lessons"] == 1
    assert summary_payload["completion_rate"] == 100.0

    client.close()

    restarted_client = build_client(database_path)
    restarted_login = restarted_client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert restarted_login.status_code == 200
    restarted_payload = restarted_login.json()
    restarted_headers = {"Authorization": f"Bearer {restarted_payload['access_token']}"}

    persisted_progress_response = restarted_client.get(
        "/api/v1/progress/lessons/understanding-periods",
        headers=restarted_headers,
    )
    assert persisted_progress_response.status_code == 200
    assert persisted_progress_response.json()["status"] == "completed"

    persisted_list_response = restarted_client.get("/api/v1/progress", headers=restarted_headers)
    assert persisted_list_response.status_code == 200
    assert len(persisted_list_response.json()) == 1
