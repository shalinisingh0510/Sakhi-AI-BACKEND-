from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings
from app.schemas.ai import ConversationDetail, ConversationMessage, ConversationSummary
from app.schemas.auth import SUPPORTED_LANGUAGES
from app.services.ai_providers import AIProviderProtocol, build_ai_provider

SUPPORTED_LANGUAGE_SET = {language.lower() for language in SUPPORTED_LANGUAGES}
DEFAULT_CONVERSATION_LANGUAGE = "english"
DEFAULT_CONVERSATION_TITLE = "Health guidance"


class ConversationError(Exception):
    """Base exception for conversation failures."""


class ConversationNotFoundError(ConversationError):
    pass


class ConversationAccessDeniedError(ConversationError):
    pass


class InvalidConversationMessageError(ConversationError):
    pass


@dataclass(slots=True)
class StoredConversation:
    id: str
    user_id: str
    title: str
    preferred_language: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    def to_summary(self) -> ConversationSummary:
        return ConversationSummary.model_validate(self)


@dataclass(slots=True)
class StoredConversationMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime

    def to_message(self) -> ConversationMessage:
        return ConversationMessage.model_validate(self)


class ConversationStoreProtocol(Protocol):
    def create_conversation(
        self,
        *,
        user_id: str,
        title: str,
        preferred_language: str,
    ) -> StoredConversation:
        ...

    def get_conversation(self, conversation_id: str) -> StoredConversation | None:
        ...

    def list_conversations(self, user_id: str) -> list[StoredConversation]:
        ...

    def get_messages(self, conversation_id: str) -> list[StoredConversationMessage]:
        ...

    def add_message(self, *, conversation_id: str, role: str, content: str) -> StoredConversationMessage:
        ...

    def update_conversation_timestamp(self, conversation_id: str) -> None:
        ...


class AIService:
    def __init__(
        self,
        settings: Settings,
        store: ConversationStoreProtocol,
        provider: AIProviderProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._provider: AIProviderProtocol = provider or build_ai_provider(settings)

    def create_conversation(
        self,
        *,
        user_id: str,
        title: str | None,
        initial_message: str,
        preferred_language: str | None = None,
    ) -> ConversationDetail:
        language = self._normalize_language(preferred_language)
        conversation_title = self._normalize_title(title, initial_message)
        conversation = self._store.create_conversation(
            user_id=user_id,
            title=conversation_title,
            preferred_language=language,
        )
        self._store.add_message(conversation_id=conversation.id, role="user", content=initial_message)
        self._store.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=self._provider.generate_reply(
                user_message=initial_message,
                conversation_title=conversation.title,
                preferred_language=conversation.preferred_language,
                history=[],
            ),
        )
        return self.get_conversation(user_id=user_id, conversation_id=conversation.id)

    def list_conversations(self, *, user_id: str) -> list[ConversationSummary]:
        return [conversation.to_summary() for conversation in self._store.list_conversations(user_id)]

    def get_conversation(self, *, user_id: str, conversation_id: str) -> ConversationDetail:
        conversation = self._require_owned_conversation(user_id=user_id, conversation_id=conversation_id)
        messages = [message.to_message() for message in self._store.get_messages(conversation_id)]
        return ConversationDetail(conversation=conversation.to_summary(), messages=messages)

    def send_message(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str,
    ) -> ConversationDetail:
        conversation = self._require_owned_conversation(user_id=user_id, conversation_id=conversation_id)
        self._store.add_message(conversation_id=conversation.id, role="user", content=message)
        # Build recent history for context-aware replies (respects history limit)
        history = self._build_history(conversation_id=conversation.id, exclude_last_n=0)
        reply_text = self._provider.generate_reply(
            user_message=message,
            conversation_title=conversation.title,
            preferred_language=conversation.preferred_language,
            history=history,
        )
        self._store.add_message(conversation_id=conversation.id, role="assistant", content=reply_text)
        return self.get_conversation(user_id=user_id, conversation_id=conversation.id)

    def _require_owned_conversation(self, *, user_id: str, conversation_id: str) -> StoredConversation:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError("Conversation not found.")
        return conversation

    def _normalize_title(self, title: str | None, initial_message: str) -> str:
        if title:
            return title.strip() or DEFAULT_CONVERSATION_TITLE
        snippet = " ".join(initial_message.strip().split())
        if not snippet:
            return DEFAULT_CONVERSATION_TITLE
        return snippet[:60] if len(snippet) <= 60 else f"{snippet[:57].rstrip()}..."

    def _normalize_language(self, preferred_language: str | None) -> str:
        normalized = (preferred_language or DEFAULT_CONVERSATION_LANGUAGE).strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_SET:
            return DEFAULT_CONVERSATION_LANGUAGE
        return normalized

    def _build_history(
        self,
        *,
        conversation_id: str,
        exclude_last_n: int = 0,
    ) -> list[dict[str, str]]:
        """
        Return the recent message history as a list of OpenAI-compatible
        {role, content} dicts, capped to `conversation_history_limit` messages.
        `exclude_last_n` allows omitting the last N messages (e.g. the user
        message that was just appended before this call).
        """
        messages = self._store.get_messages(conversation_id)
        if exclude_last_n:
            messages = messages[:-exclude_last_n]
        limit = self._settings.conversation_history_limit
        recent = messages[-limit:] if len(messages) > limit else messages
        return [{"role": msg.role, "content": msg.content} for msg in recent]
