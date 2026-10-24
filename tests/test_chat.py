from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

REGISTER_USER = {
    'name': 'Asha Verma',
    'email': 'asha.verma@sakhi.ai',
    'password': 'StrongPass123!',
}


def build_client(database_url: str | Path) -> TestClient:
    db_str = str(database_url)
    if not (db_str.startswith("sqlite:") or db_str.startswith("postgresql:") or db_str.startswith("postgres:")):
        db_str = f"sqlite:///{db_str}"
    settings = Settings(database_url=db_str)
    return TestClient(create_app(settings=settings))


def _register_user(client: TestClient, email: str | None = None) -> str:
    user_data = dict(REGISTER_USER)
    user_data['email'] = email or f'user_{uuid.uuid4().hex[:8]}@sakhi.ai'
    response = client.post('/api/v1/auth/register', json=user_data)
    if response.status_code == 409:
        login = client.post('/api/v1/auth/login', json={'email': user_data['email'], 'password': user_data['password']})
        assert login.status_code == 200
        return login.json()['access_token']
    assert response.status_code == 201
    return response.json()['access_token']


def test_chat_message_creates_conversation_and_returns_temporary_reply(test_db_url: str) -> None:
    client = build_client(test_db_url)
    token = _register_user(client)

    response = client.post(
        '/api/v1/chat/message',
        json={'message': 'Why are my periods irregular?', 'preferred_language': 'english'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['conversation']['message_count'] == 2
    assert payload['messages'][0]['role'] == 'user'
    assert payload['messages'][1]['role'] == 'assistant'
    assert "not a diagnosis" in payload['messages'][1]['content']

    client.close()


def test_chat_message_reuses_existing_conversation(test_db_url: str) -> None:
    client = build_client(test_db_url)

    token = _register_user(client)
    first_response = client.post(
        '/api/v1/chat/message',
        json={'message': 'Initial question.'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert first_response.status_code == 200
    conversation_id = first_response.json()['conversation']['id']

    second_response = client.post(
        '/api/v1/chat/message',
        json={'message': 'Follow-up question.', 'conversationId': conversation_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload['conversation']['id'] == conversation_id
    assert len(payload['messages']) == 4
    assert "not a diagnosis" in payload['messages'][-1]['content']


def test_chat_message_rejects_invalid_inputs(test_db_url: str) -> None:
    client = build_client(test_db_url)
    token = _register_user(client)
    headers = {'Authorization': f'Bearer {token}'}

    for message in ['', '   ', 'x' * 4001]:
        response = client.post(
            '/api/v1/chat/message',
            json={'message': message},
            headers=headers,
        )
        assert response.status_code == 422

    invalid_conversation_response = client.post(
        '/api/v1/chat/message',
        json={'conversation_id': 'not-a-valid-id', 'message': 'Hello'},
        headers=headers,
    )
    assert invalid_conversation_response.status_code == 422


def test_chat_message_requires_authentication(test_db_url: str) -> None:
    client = build_client(test_db_url)

    response = client.post(
        '/api/v1/chat/message',
        json={'message': 'Hello'},
    )

    assert response.status_code == 401


def test_chat_message_enforces_conversation_ownership(test_db_url: str) -> None:
    client = build_client(test_db_url)

    owner_token = _register_user(client, email=f'owner_{uuid.uuid4().hex[:8]}@sakhi.ai')
    owner_headers = {'Authorization': f'Bearer {owner_token}'}
    create_response = client.post(
        '/api/v1/chat/message',
        json={'message': 'I feel anxious about school.'},
        headers=owner_headers,
    )
    assert create_response.status_code == 200
    conversation_id = create_response.json()['conversation']['id']

    second_token = _register_user(client, email=f'second_{uuid.uuid4().hex[:8]}@sakhi.ai')
    second_headers = {'Authorization': f'Bearer {second_token}'}

    response = client.post(
        '/api/v1/chat/message',
        json={'conversation_id': conversation_id, 'message': 'Is this my conversation?'},
        headers=second_headers,
    )

    assert response.status_code == 404
