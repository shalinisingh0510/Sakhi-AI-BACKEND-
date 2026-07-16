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


def test_conversation_creation_message_and_persistence_flow(tmp_path: Path) -> None:
    database_path = tmp_path / "conversations.sqlite3"
    client = build_client(database_path)

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]

    create_response = client.post(
        "/api/v1/conversations",
        json={
            "title": "Cycle questions",
            "initial_message": "I want to understand period cramps and what is normal.",
            "preferred_language": "english",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["conversation"]["title"] == "Cycle questions"
    assert create_payload["conversation"]["message_count"] == 2
    assert len(create_payload["messages"]) == 2
    assert create_payload["messages"][0]["role"] == "user"
    assert create_payload["messages"][1]["role"] == "assistant"
    assert create_payload["messages"][1]["content"].startswith("We are continuing the conversation")

    conversation_id = create_payload["conversation"].get("id")
    message_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"message": "Can hydration help with cramps?"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert message_response.status_code == 200
    message_payload = message_response.json()
    assert message_payload["conversation"]["message_count"] == 4
    assert [message["role"] for message in message_payload["messages"]] == ["user", "assistant", "user", "assistant"]
    assert message_payload["messages"][-1]["content"].startswith("We are continuing the conversation")

    client.close()

    second_client = build_client(database_path)
    list_response = second_client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["message_count"] == 4

    detail_response = second_client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["conversation"]["message_count"] == 4
    assert len(detail_response.json()["messages"]) == 4


def test_conversation_is_private_to_owner(tmp_path: Path) -> None:
    database_path = tmp_path / "conversations-private.sqlite3"
    client = build_client(database_path)

    user_one = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert user_one.status_code == 201
    user_one_token = user_one.json()["access_token"]

    create_response = client.post(
        "/api/v1/conversations",
        json={"initial_message": "I feel anxious about school."},
        headers={"Authorization": f"Bearer {user_one_token}"},
    )
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversation"]["id"]

    other_user = client.post(
        "/api/v1/auth/register",
        json={"name": "Leela Rao", "email": "leela.rao@sakhi.ai", "password": "StrongPass123!"},
    )
    assert other_user.status_code == 201
    other_token = other_user.json()["access_token"]

    forbidden_response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden_response.status_code == 404
