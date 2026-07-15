from fastapi.testclient import TestClient

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


def test_auth_registration_login_and_profile_flow() -> None:
    client = TestClient(create_app())

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["user"]["email"] == REGISTER_USER["email"]
    assert register_payload["user"]["role"] == "user"

    access_token = register_payload["access_token"]
    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == REGISTER_USER["email"]

    login_response = client.post("/api/v1/auth/login", json=REGISTER_USER)
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == REGISTER_USER["email"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": register_payload["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["user"]["email"] == REGISTER_USER["email"]


def test_admin_route_requires_admin_role() -> None:
    client = TestClient(create_app())

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201

    access_token = register_response.json()["access_token"]
    admin_response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert admin_response.status_code == 403


def test_admin_route_allows_admin_role() -> None:
    client = TestClient(create_app())

    register_response = client.post("/api/v1/auth/register", json=REGISTER_ADMIN)
    assert register_response.status_code == 201

    access_token = register_response.json()["access_token"]
    admin_response = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["message"] == "Admin access granted"
