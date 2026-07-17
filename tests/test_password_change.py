"""Tests for the password change endpoint."""
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


def test_user_can_change_password(tmp_path: Path) -> None:
    client = build_client(tmp_path / "pw-change.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        },
        headers=headers,
    )
    assert change_response.status_code == 204

    # Old password should no longer work
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": "StrongPass123!"},
    )
    assert old_login.status_code == 401

    # New password should work
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": "NewStrongPass456!"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["email"] == REGISTER_USER["email"]


def test_change_password_rejects_wrong_current_password(tmp_path: Path) -> None:
    client = build_client(tmp_path / "pw-wrong.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "WrongPassword999!",
            "new_password": "NewStrongPass456!",
        },
        headers=headers,
    )
    assert change_response.status_code == 401
    assert "incorrect" in change_response.json()["detail"].lower()


def test_change_password_rejects_same_password(tmp_path: Path) -> None:
    client = build_client(tmp_path / "pw-same.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "StrongPass123!",
            "new_password": "StrongPass123!",
        },
        headers=headers,
    )
    assert change_response.status_code == 400
    assert "different" in change_response.json()["detail"].lower()


def test_change_password_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "pw-unauth.sqlite3")

    change_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        },
    )
    assert change_response.status_code == 401


def test_password_change_persists_across_app_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "pw-persist.sqlite3"
    client = build_client(database_path)

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "StrongPass123!",
            "new_password": "PersistPass789!",
        },
        headers=headers,
    )
    assert change_response.status_code == 204
    client.close()

    # Second instance — new password must still work
    second_client = build_client(database_path)
    login_response = second_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": "PersistPass789!"},
    )
    assert login_response.status_code == 200
