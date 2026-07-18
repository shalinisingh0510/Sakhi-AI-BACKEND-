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


def test_auth_registration_login_profile_and_preference_update_flow(tmp_path: Path) -> None:
    client = build_client(tmp_path / "auth.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["user"]["email"] == REGISTER_USER["email"]
    assert register_payload["user"]["role"] == "user"
    assert register_payload["user"]["preferred_language"] == "english"

    access_token = register_payload["access_token"]
    update_response = client.patch(
        "/api/v1/auth/me",
        json={"name": "Asha Sharma", "preferred_language": "hindi"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["name"] == "Asha Sharma"
    assert update_payload["preferred_language"] == "hindi"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Asha Sharma"
    assert me_response.json()["preferred_language"] == "hindi"

    login_response = client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == REGISTER_USER["email"]
    assert login_response.json()["user"]["preferred_language"] == "hindi"

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": register_payload["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["user"]["email"] == REGISTER_USER["email"]
    assert refreshed_payload["refresh_token"] != register_payload["refresh_token"]

    reused_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": register_payload["refresh_token"]},
    )
    assert reused_refresh_response.status_code == 401

    second_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed_payload["refresh_token"]},
    )
    assert second_refresh_response.status_code == 200


def test_registered_user_persists_across_app_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent-auth.sqlite3"

    first_client = build_client(database_path)
    register_response = first_client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    first_client.close()

    second_client = build_client(database_path)
    login_response = second_client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == REGISTER_USER["email"]


def test_admin_route_requires_admin_role(tmp_path: Path) -> None:
    client = build_client(tmp_path / "admin-role.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201

    access_token = register_response.json()["access_token"]
    admin_response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert admin_response.status_code == 403


def test_admin_route_allows_admin_role(tmp_path: Path) -> None:
    client = build_client(tmp_path / "admin-success.sqlite3")

    register_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert register_response.status_code == 201

    access_token = register_response.json()["access_token"]
    admin_response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["message"] == "Admin access granted"


def test_admin_can_list_users_and_change_role(tmp_path: Path) -> None:
    client = build_client(tmp_path / "role-management.sqlite3")

    user_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_response.status_code == 201
    user_id = user_response.json()["user"]["id"]

    admin_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert admin_response.status_code == 201
    admin_token = admin_response.json()["access_token"]

    list_response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    listed_emails = {user["email"] for user in list_response.json()}
    assert REGISTER_USER["email"] in listed_emails
    assert REGISTER_ADMIN["email"] in listed_emails

    role_response = client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "moderator"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert role_response.status_code == 200
    assert role_response.json()["role"] == "moderator"

    moderator_login = client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert moderator_login.status_code == 200
    assert moderator_login.json()["user"]["role"] == "moderator"

    moderator_token = moderator_login.json()["access_token"]
    forbidden_response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {moderator_token}"},
    )
    assert forbidden_response.status_code == 403
