"""Tests for the pluggable AI provider abstraction."""
from __future__ import annotations

import builtins
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.ai_providers import RuleBasedProvider, OpenAIProvider, build_ai_provider


REGISTER_USER = {
    "name": "Asha Verma",
    "email": "asha.verma@sakhi.ai",
    "password": "StrongPass123!",
}


def build_client(database_path: Path, **settings_overrides) -> TestClient:
    settings = Settings(database_path=database_path, **settings_overrides)
    return TestClient(create_app(settings=settings))


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def test_build_ai_provider_returns_rule_based_by_default() -> None:
    settings = Settings(ai_provider_name="rule-based")
    provider = build_ai_provider(settings)
    assert isinstance(provider, RuleBasedProvider)


def test_build_ai_provider_falls_back_for_unknown_name() -> None:
    settings = Settings(ai_provider_name="totally-unknown")
    provider = build_ai_provider(settings)
    assert isinstance(provider, RuleBasedProvider)


def test_build_ai_provider_falls_back_for_openai_without_key() -> None:
    settings = Settings(ai_provider_name="openai", openai_api_key=None)
    provider = build_ai_provider(settings)
    assert isinstance(provider, RuleBasedProvider)


# ---------------------------------------------------------------------------
# RuleBasedProvider content correctness
# ---------------------------------------------------------------------------

def test_rule_based_menstrual_topic() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="I have bad period cramps",
        conversation_title="Health Q&A",
        preferred_language="english",
        history=[],
    )
    assert any(kw in reply.lower() for kw in ("cramp", "menstrual", "period", "cycle"))
    assert "educational" in reply.lower()
    assert "diagnosis" in reply.lower()


def test_rule_based_mental_health_topic() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="I feel very anxious about school",
        conversation_title="Mental Wellness",
        preferred_language="english",
        history=[],
    )
    assert any(kw in reply.lower() for kw in ("stress", "anxious", "emotional", "overwhelm"))


def test_rule_based_pregnancy_topic() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="Questions about fertility and ovulation",
        conversation_title="Reproductive Health",
        preferred_language="english",
        history=[],
    )
    assert any(kw in reply.lower() for kw in ("fertility", "pregnan", "medical", "healthcare"))


def test_rule_based_hygiene_topic() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="I have unusual discharge and itching",
        conversation_title="Hygiene Questions",
        preferred_language="english",
        history=[],
    )
    assert any(kw in reply.lower() for kw in ("hygiene", "discharge", "clean", "irritat"))


def test_rule_based_general_topic() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="Tell me something about health",
        conversation_title="General",
        preferred_language="english",
        history=[],
    )
    assert len(reply) > 30
    assert "educational" in reply.lower()


def test_rule_based_includes_language_hint_for_non_english() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="Some health question",
        conversation_title="Health",
        preferred_language="hindi",
        history=[],
    )
    assert "(hindi)" in reply.lower()


def test_rule_based_no_language_hint_for_english() -> None:
    provider = RuleBasedProvider()
    reply = provider.generate_reply(
        user_message="Some health question",
        conversation_title="Health",
        preferred_language="english",
        history=[],
    )
    assert "(english)" not in reply.lower()


# ---------------------------------------------------------------------------
# OpenAIProvider fallback when package is missing
# ---------------------------------------------------------------------------

def test_openai_provider_falls_back_when_package_missing(monkeypatch) -> None:
    """OpenAIProvider must degrade gracefully when openai is not installed."""
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("simulated: openai not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
    reply = provider.generate_reply(
        user_message="Period cramps",
        conversation_title="Health",
        preferred_language="english",
        history=[],
    )
    # Should get a rule-based response, not raise
    assert len(reply) > 10
    assert "educational" in reply.lower()


# ---------------------------------------------------------------------------
# Integration: provider wired into AIService via API
# ---------------------------------------------------------------------------

def test_conversation_uses_rule_based_provider_by_default(tmp_path: Path) -> None:
    client = build_client(tmp_path / "ai-provider.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    resp = client.post(
        "/api/v1/conversations",
        json={"initial_message": "I have severe period cramps"},
        headers=headers,
    )
    assert resp.status_code == 201
    assistant_reply = resp.json()["messages"][1]["content"]
    assert "educational" in assistant_reply.lower()
    assert "diagnosis" in assistant_reply.lower()


def test_conversation_history_is_stored_and_accessible(tmp_path: Path) -> None:
    client = build_client(tmp_path / "ai-history.sqlite3")

    reg = client.post("/api/v1/auth/register", json=REGISTER_USER)
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    create = client.post(
        "/api/v1/conversations",
        json={"initial_message": "Tell me about menstrual health"},
        headers=headers,
    )
    assert create.status_code == 201
    conv_id = create.json()["conversation"]["id"]

    follow = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"message": "What about managing stress during my period?"},
        headers=headers,
    )
    assert follow.status_code == 200
    assert follow.json()["conversation"]["message_count"] == 4
    roles = [m["role"] for m in follow.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
