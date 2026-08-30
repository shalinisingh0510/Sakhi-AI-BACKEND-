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


def build_client(database_url: str) -> TestClient:
    settings = Settings(database_url=database_url)
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


def test_chat_message_creates_conversation_and_returns_temporary_reply(tmp_path: Path) -> None:
    database_path = tmp_path / 'chat.sqlite3'
    client = build_client(database_path)
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
    assert payload['messages'][1]['content'].startswith('Thanks, your message reached Sakhi Chat.')
    assert "not a diagnosis" in payload['messages'][1]['content']

    client.close()


def test_chat_message_reuses_existing_conversation(tmp_path: Path) -> None:
    database_path = tmp_path / 'chat-existing.sqlite3'
    client = build_client(database_path)
    settings = Settings(database_url=f'sqlite:///{database_path}')
    client = TestClient(create_app(settings=settings))

    token = _register_user(client)
    headers = {'Authorization': f'Bearer {token}'}

    first_response = client.post(
        '/api/v1/chat/message',
        json={'message': 'I want to understand menstrual cramps.'},
        headers=headers,
        json={'message': 'Initial question.'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert first_response.status_code == 200
    conversation_id = first_response.json()['conversation']['id']

    second_response = client.post(
        '/api/v1/chat/message',
        json={'conversation_id': conversation_id, 'message': 'Can hydration help?'},
        headers=headers,
        json={'message': 'Follow-up question.', 'conversationId': conversation_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload['conversation']['message_count'] == 4
    assert [message['role'] for message in payload['messages']] == ['user', 'assistant', 'user', 'assistant']
    assert payload['messages'][-1]['content'].startswith('Thanks, your message reached Sakhi Chat.')
    assert payload['conversation']['id'] == conversation_id
    assert len(payload['messages']) == 4
    assert "not a diagnosis" in payload['messages'][-1]['content']


def test_chat_message_rejects_invalid_inputs(tmp_path: Path) -> None:
    database_path = tmp_path / 'chat-validation.sqlite3'
    client = build_client(database_path)
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


def test_chat_message_requires_authentication(tmp_path: Path) -> None:
    database_path = tmp_path / 'chat-auth.sqlite3'
    client = build_client(database_path)

    response = client.post(
        '/api/v1/chat/message',
        json={'message': 'Hello'},
    )

    assert response.status_code == 401


def test_chat_message_enforces_conversation_ownership(tmp_path: Path) -> None:
    database_path = tmp_path / 'chat-ownership.sqlite3'
    client = build_client(database_path)

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
