from __future__ import annotations

from app.core.config import Settings
from app.schemas.auth import SUPPORTED_LANGUAGES
from app.schemas.chat import ChatMessageContent, ChatMessageData
from app.services.ai import (
    ConversationNotFoundError,
    ConversationStoreProtocol,
    StoredConversation,
)

SUPPORTED_LANGUAGE_SET = {lang.lower() for lang in SUPPORTED_LANGUAGES}
DEFAULT_LANGUAGE = "english"
DEFAULT_TITLE = "Health guidance"


def generate_temporary_response(message: str, language: str) -> str:
    """
    Generate a controlled temporary assistant response for Phase 2.
    Proves the end-to-end Chat API integration without external LLM or RAG dependencies.
    """
    msg_lower = message.lower()
    
    if any(k in msg_lower for k in ("cramp", "period", "menstrual", "cycle", "bleed")):
        guidance = (
            "Menstrual cramps and cycle fluctuations are common experiences. "
            "Gentle rest, adequate hydration, and a warm compress may offer comfort. "
            "If you experience severe pain, unusually heavy bleeding, or dizziness, "
            "please consult a qualified healthcare professional."
        )
    elif any(k in msg_lower for k in ("hygiene", "clean", "wash", "pad", "tampon", "cup")):
        guidance = (
            "Maintaining clean and dry intimate hygiene is important for your wellbeing. "
            "Change menstrual products regularly (every 4-6 hours for pads) and wash with plain water, "
            "avoiding harsh scented soaps."
        )
    elif any(k in msg_lower for k in ("stress", "anxiety", "anxious", "mood", "sad", "feel")):
        guidance = (
            "Emotional wellbeing and physical health are closely connected. "
            "Taking deep breaths, getting adequate sleep, and speaking with someone you trust can help. "
            "If emotional distress persists, professional support is always recommended."
        )
    else:
        guidance = (
            "I have received your message regarding women's health. "
            "Sakhi is here to provide calm, trusted, and culturally sensitive educational guidance. "
            "Feel free to ask more specific questions about periods, hygiene, or wellbeing."
        )

    return (
        f"{guidance} "
        f"[Sakhi Chat Service Response. Educational only; not medical advice.]"
    )


class ChatService:
    """
    Chat service orchestrating chat conversation lifecycle,
    message validation, ownership verification, and response generation.
    """

    def __init__(self, settings: Settings, store: ConversationStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def process_chat_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        language: str | None = None,
    ) -> ChatMessageData:
        target_language = self._normalize_language(language)

        # 1. Resolve or create conversation
        if conversation_id:
            conversation = self._get_owned_conversation(user_id=user_id, conversation_id=conversation_id)
        else:
            title = self._derive_title(message)
            conversation = self._store.create_conversation(
                user_id=user_id,
                title=title,
                preferred_language=target_language,
            )

        # 2. Persist the incoming user message
        self._store.add_message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )

        # 3. Generate the temporary assistant response (Phase 2 controlled response)
        reply_content = generate_temporary_response(message, conversation.preferred_language or target_language)

        # 4. Persist the assistant message
        stored_assistant_msg = self._store.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply_content,
        )

        # 5. Return structured response payload
        return ChatMessageData(
            conversation_id=conversation.id,
            conversationId=conversation.id,
            message=ChatMessageContent(
                id=stored_assistant_msg.id,
                role="assistant",
                content=stored_assistant_msg.content,
                created_at=stored_assistant_msg.created_at,
            ),
        )

    def _get_owned_conversation(self, *, user_id: str, conversation_id: str) -> StoredConversation:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError("Conversation not found or access denied.")
        return conversation

    def _derive_title(self, message: str) -> str:
        cleaned = " ".join(message.strip().split())
        if not cleaned:
            return DEFAULT_TITLE
        if len(cleaned) <= 50:
            return cleaned
        return f"{cleaned[:47].rstrip()}..."

    def _normalize_language(self, language: str | None) -> str:
        if not language:
            return DEFAULT_LANGUAGE
        norm = language.strip().lower()
        if norm in SUPPORTED_LANGUAGE_SET:
            return norm
        return DEFAULT_LANGUAGE
