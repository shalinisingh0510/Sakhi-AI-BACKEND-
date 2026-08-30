from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

USER_A = {
    "name": "Priya Sharma",
    "email": "priya.sharma@sakhi.ai",
    "password": "SecurePassword123!",
}

USER_B = {
    "name": "Ananya Patel",
    "email": "ananya.patel@sakhi.ai",
    "password": "SecurePassword456!",
}


def build_client(database_url: str) -> TestClient:
    settings = Settings(database_url=database_url)
    return TestClient(create_app(settings=settings))


def test_1_valid_message_creates_conversation_and_returns_assistant_reply(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)

    # Register user
    reg = client.post("/api/v1/auth/register", json=USER_A)
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    # Send valid chat message
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "What are common causes of irregular periods?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "conversationId" in data or "conversation_id" in data
    conv_id = data.get("conversationId") or data.get("conversation_id")
    assert conv_id is not None
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0
    assert "Sakhi Chat Service Response" in data["message"]["content"]
    assert "not a diagnosis" in data["message"]["content"]


def test_2_empty_message_validation_error(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)
    reg = client.post("/api/v1/auth/register", json=USER_A)
    token = reg.json()["access_token"]

    response = client.post(
        "/api/v1/chat/message",
        json={"message": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_3_whitespace_only_message_validation_error(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)
    reg = client.post("/api/v1/auth/register", json=USER_A)
    token = reg.json()["access_token"]

    response = client.post(
        "/api/v1/chat/message",
        json={"message": "   \n\t  "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_4_excessively_long_message_validation_error(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)
    reg = client.post("/api/v1/auth/register", json=USER_A)
    token = reg.json()["access_token"]

    long_message = "a" * 4001
    response = client.post(
        "/api/v1/chat/message",
        json={"message": long_message},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_5_unauthorized_request(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)

    # Missing auth
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "How do I maintain menstrual hygiene?"},
    )
    assert response.status_code == 401

    # Invalid token
    response_invalid = client.post(
        "/api/v1/chat/message",
        json={"message": "How do I maintain menstrual hygiene?"},
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response_invalid.status_code == 401


def test_6_invalid_conversation_id(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)
    reg = client.post("/api/v1/auth/register", json=USER_A)
    token = reg.json()["access_token"]

    response = client.post(
        "/api/v1/chat/message",
        json={
            "conversationId": "non-existent-conversation-id-12345",
            "message": "Why do I feel cramps?",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_7_conversation_ownership_isolation(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)

    # User A registers & creates conversation
    reg_a = client.post("/api/v1/auth/register", json=USER_A)
    token_a = reg_a.json()["access_token"]

    resp_a = client.post(
        "/api/v1/chat/message",
        json={"message": "Hello from User A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    conv_id_a = resp_a.json()["data"]["conversationId"]

    # User B registers
    reg_b = client.post("/api/v1/auth/register", json=USER_B)
    token_b = reg_b.json()["access_token"]

    # User B attempts to access / post to User A's conversation
    resp_b = client.post(
        "/api/v1/chat/message",
        json={
            "conversationId": conv_id_a,
            "message": "Hello from User B trying to breach User A conversation",
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 404


def test_8_multiple_messages_in_same_conversation(tmp_path: Path, test_db_url: str) -> None:
    client = build_client(test_db_url)

    reg = client.post("/api/v1/auth/register", json=USER_A)
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First message -> creates conversation
    msg1 = client.post(
        "/api/v1/chat/message",
        json={"message": "What is puberty?"},
        headers=headers,
    )
    assert msg1.status_code == 200
    conv_id = msg1.json()["data"]["conversationId"]

    # Second message in same conversation
    msg2 = client.post(
        "/api/v1/chat/message",
        json={
            "conversationId": conv_id,
            "message": "What bodily changes occur during puberty?",
        },
        headers=headers,
    )
    assert msg2.status_code == 200
    assert msg2.json()["data"]["conversationId"] == conv_id

    # Third message in same conversation
    msg3 = client.post(
        "/api/v1/chat/message",
        json={
            "conversationId": conv_id,
            "message": "How can I speak to a doctor about cramps?",
        },
        headers=headers,
    )
    assert msg3.status_code == 200
    assert msg3.json()["data"]["conversationId"] == conv_id

    # Verify conversation messages in database
    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["conversation"]["message_count"] == 6  # 3 user + 3 assistant
    roles = [m["role"] for m in detail_data["messages"]]
    assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]
