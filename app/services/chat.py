from __future__ import annotations

from app.core.config import Settings
from app.schemas.ai import ConversationDetail
from app.schemas.auth import SUPPORTED_LANGUAGES
from app.schemas.chat import ChatMessageContent, ChatMessageData, ChatMessageResponse
from app.services.ai import ConversationNotFoundError, ConversationStoreProtocol, StoredConversation

SUPPORTED_LANGUAGE_SET = {lang.lower() for lang in SUPPORTED_LANGUAGES}
DEFAULT_LANGUAGE = "english"
DEFAULT_TITLE = "Health guidance"
TEMPORARY_CHAT_REPLY = (
    "Thanks, your message reached Sakhi Chat. "
    "Sakhi Chat Service Response is a temporary backend response while the full assistant is being connected."
)


class ChatService:
    def __init__(self, settings: Settings, store: ConversationStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def process_chat_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        preferred_language: str | None = None,
        language: str | None = None,
        mode: str = "text",
    ) -> ChatMessageResponse:
        target_language = self._normalize_language(language or preferred_language)
        detail = self.send_message(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
            preferred_language=target_language,
            mode=mode,
        )
        assistant_message = detail.messages[-1] if detail.messages else None
        if assistant_message is None:
            raise RuntimeError("Assistant message was not stored.")

        return ChatMessageResponse(
            success=True,
            data=ChatMessageData(
                conversation_id=detail.conversation.id,
                message=ChatMessageContent.model_validate(assistant_message),
            ),
            conversation=detail.conversation,
            messages=detail.messages,
        )

    def send_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        preferred_language: str = "english",
        mode: str = "text",
    ) -> ConversationDetail:
        conversation = self._resolve_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            initial_message=message,
            preferred_language=self._normalize_language(preferred_language),
        )

        self._store.add_message(conversation_id=conversation.id, role="user", content=message)
        self._store.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=self._build_temporary_reply(mode=mode),
        )
        return self.get_conversation(user_id=user_id, conversation_id=conversation.id)

    def get_conversation(self, *, user_id: str, conversation_id: str) -> ConversationDetail:
        conversation = self._require_owned_conversation(user_id=user_id, conversation_id=conversation_id)
        messages = [message.to_message() for message in self._store.get_messages(conversation_id)]
        return ConversationDetail(conversation=conversation.to_summary(), messages=messages)

    def _resolve_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        initial_message: str,
        preferred_language: str,
    ) -> StoredConversation:
        if conversation_id is not None:
            return self._require_owned_conversation(user_id=user_id, conversation_id=conversation_id)

        return self._store.create_conversation(
            user_id=user_id,
            title=self._build_conversation_title(initial_message),
            preferred_language=preferred_language,
        )

    def _require_owned_conversation(self, *, user_id: str, conversation_id: str) -> StoredConversation:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError("Conversation not found or access denied.")
        return conversation

    def _build_conversation_title(self, message: str) -> str:
        snippet = " ".join(message.strip().split())
        if not snippet:
            return DEFAULT_TITLE
        if len(snippet) <= 60:
            return snippet
        return f"{snippet[:57].rstrip()}..."

    def _normalize_language(self, language: str | None) -> str:
        if not language:
            return DEFAULT_LANGUAGE
        normalized = language.strip().lower()
        if normalized in SUPPORTED_LANGUAGE_SET:
            return normalized
        return DEFAULT_LANGUAGE

    def _build_temporary_reply(self, *, mode: str) -> str:
        if mode == "voice":
            return TEMPORARY_CHAT_REPLY
        return TEMPORARY_CHAT_REPLY
