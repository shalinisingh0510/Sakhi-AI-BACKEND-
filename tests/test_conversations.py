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


def build_client(database_url: str) -> TestClient:
    settings = Settings(database_url=database_url)
    return TestClient(create_app(settings=settings))


def test_conversation_creation_message_and_persistence_flow(tmp_path: Path, test_db_url: str) -> None:
    database_path = test_db_url
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


def test_conversation_is_private_to_owner(tmp_path: Path, test_db_url: str) -> None:
    database_path = test_db_url
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


def test_follow_up_message_uses_history_without_duplication(tmp_path: Path, test_db_url: str) -> None:
    database_path = test_db_url
    client = build_client(database_path)

    register_response = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert register_response.status_code == 201
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    class CaptureProvider:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def generate_reply(
            self,
            *,
            user_message: str,
            conversation_title: str,
            preferred_language: str,
            history: list[dict[str, str]],
        ) -> str:
            self.calls.append(
                {
                    "user_message": user_message,
                    "conversation_title": conversation_title,
                    "preferred_language": preferred_language,
                    "history": [dict(message) for message in history],
                }
            )
            return f"captured reply {len(self.calls)}"

    provider = CaptureProvider()
    client.app.state.ai_service._provider = provider

    create_response = client.post(
        "/api/v1/conversations",
        json={"initial_message": "Tell me about menstrual health"},
        headers=headers,
    )
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversation"]["id"]

    follow_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"message": "Can hydration help with cramps?"},
        headers=headers,
    )
    assert follow_response.status_code == 200
    assert len(provider.calls) == 2

    follow_up_call = provider.calls[1]
    assert follow_up_call["user_message"] == "Can hydration help with cramps?"
    history = follow_up_call["history"]
    assert len(history) == 2
    assert [message["role"] for message in history] == ["user", "assistant"]
    assert history[-1]["content"] != "Can hydration help with cramps?"
