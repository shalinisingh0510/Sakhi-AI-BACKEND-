"""Tests for logout (token revocation) and account deletion."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.token_blacklist import TokenBlacklist
from app.main import create_app

REGISTER_USER = {
    "name": "Asha Verma",
    "email": "asha.verma@sakhi.ai",
    "password": "StrongPass123!",
}

REGISTER_USER_2 = {
    "name": "Priya Singh",
    "email": "priya.singh@sakhi.ai",
    "password": "StrongPass456!",
}


def build_client(database_path: Path) -> TestClient:
    settings = Settings(database_path=database_path)
    return TestClient(create_app(settings=settings))


# ---------------------------------------------------------------------------
# Logout / token revocation
# ---------------------------------------------------------------------------

def test_logout_revokes_token(tmp_path: Path) -> None:
    client = build_client(tmp_path / "logout.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Token works before logout
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Logout
    resp = client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 204

    # Token must now be rejected
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_logout_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "logout-unauth.sqlite3")
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


def test_logout_does_not_affect_other_tokens(tmp_path: Path) -> None:
    """Logging out one token must not invalidate other sessions."""
    client = build_client(tmp_path / "logout-multi.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    token1 = reg.json()["access_token"]

    # Obtain a second token by logging in again
    login = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": REGISTER_USER["password"]},
    )
    assert login.status_code == 200
    token2 = login.json()["access_token"]

    # Logout token1
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token1}"})

    # token1 should be rejected
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"}).status_code == 401
    # token2 should still work
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"}).status_code == 200


# ---------------------------------------------------------------------------
# Token blacklist unit tests
# ---------------------------------------------------------------------------

def test_token_blacklist_rejects_revoked_jti() -> None:
    bl = TokenBlacklist()
    import time
    future_exp = time.time() + 3600
    bl.revoke("jti-abc", future_exp)
    assert bl.is_revoked("jti-abc") is True
    assert bl.is_revoked("jti-xyz") is False


def test_token_blacklist_ignores_expired_entries() -> None:
    bl = TokenBlacklist()
    import time
    # Expire in the past
    bl.revoke("old-jti", time.time() - 1)
    assert bl.is_revoked("old-jti") is False


def test_token_blacklist_size_property() -> None:
    bl = TokenBlacklist()
    import time
    bl.revoke("jti-1", time.time() + 3600)
    bl.revoke("jti-2", time.time() + 3600)
    assert bl.size == 2


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------

def test_user_can_delete_own_account(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-account.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Account exists — login works
    assert client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": REGISTER_USER["password"]},
    ).status_code == 200

    # Delete the account
    resp = client.delete("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 204

    # Login must now fail — account gone
    assert client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": REGISTER_USER["password"]},
    ).status_code == 401


def test_account_deletion_requires_authentication(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-unauth.sqlite3")
    resp = client.delete("/api/v1/auth/me")
    assert resp.status_code == 401


def test_account_deletion_persists_across_restart(tmp_path: Path) -> None:
    db = tmp_path / "delete-persist.sqlite3"
    client = build_client(db)

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    client.delete("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    client.close()

    # New app instance — account should still be gone
    client2 = build_client(db)
    assert client2.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER["email"], "password": REGISTER_USER["password"]},
    ).status_code == 401


def test_deleted_account_email_can_be_reused(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delete-reuse.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    delete_response = client.delete("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert delete_response.status_code == 204

    rerun = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert rerun.status_code == 201
    assert rerun.json()["user"]["email"] == REGISTER_USER["email"]


def test_admin_delete_does_not_affect_other_users(tmp_path: Path) -> None:
    """Deleting one user account must not remove other accounts."""
    client = build_client(tmp_path / "delete-isolation.sqlite3")

    reg1 = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg1.status_code == 201
    token1 = reg1.json()["access_token"]

    reg2 = client.post("/api/v1/auth/register", json=REGISTER_USER_2)
    assert reg2.status_code == 201

    # Delete user 1
    client.delete("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})

    # User 2 login must still work
    assert client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_USER_2["email"], "password": REGISTER_USER_2["password"]},
    ).status_code == 200
