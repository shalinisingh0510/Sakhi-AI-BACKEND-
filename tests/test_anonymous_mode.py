from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def build_client(database_url: str) -> TestClient:
    settings = Settings(database_url=database_url)
    return TestClient(create_app(settings=settings))


def test_anonymous_mode_flow(test_db_url: str) -> None:
    client = build_client(test_db_url)

    # 1. Create Anonymous Session (Zero personal identifiers)
    anon_res = client.post("/api/v1/auth/anonymous", json={"preferred_language": "english"})
    assert anon_res.status_code == 201
    anon_data = anon_res.json()

    assert anon_data["user"]["is_anonymous"] is True
    assert anon_data["user"]["recovery_key"].startswith("SAKHI-ANON-")
    recovery_key = anon_data["user"]["recovery_key"]
    user_id = anon_data["user"]["id"]
    access_token = anon_data["access_token"]
    assert access_token

    # 2. Access /me as anonymous user
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["is_anonymous"] is True
    assert me_res.json()["id"] == user_id

    # 3. Restore session using recovery key
    restore_res = client.post("/api/v1/auth/anonymous/restore", json={"recovery_key": recovery_key})
    assert restore_res.status_code == 200
    restored_data = restore_res.json()
    assert restored_data["user"]["id"] == user_id
    assert restored_data["user"]["is_anonymous"] is True

    # 4. Reject invalid recovery key
    invalid_res = client.post("/api/v1/auth/anonymous/restore", json={"recovery_key": "SAKHI-ANON-INVALID-KEY"})
    assert invalid_res.status_code == 401

    # 5. Convert anonymous user to permanent registered account
    convert_res = client.post(
        "/api/v1/auth/anonymous/convert",
        json={
            "email": "converted.user@sakhi.ai",
            "password": "StrongPassword123!",
            "name": "Meera Patel",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert convert_res.status_code == 200
    converted_data = convert_res.json()
    assert converted_data["user"]["id"] == user_id
    assert converted_data["user"]["email"] == "converted.user@sakhi.ai"
    assert converted_data["user"]["name"] == "Meera Patel"
    assert converted_data["user"]["is_anonymous"] is False

    # 6. Cannot convert already-converted user again
    second_convert = client.post(
        "/api/v1/auth/anonymous/convert",
        json={
            "email": "another.email@sakhi.ai",
            "password": "AnotherPassword123!",
            "name": "Meera Patel",
        },
        headers={"Authorization": f"Bearer {converted_data['access_token']}"},
    )
    assert second_convert.status_code == 400
