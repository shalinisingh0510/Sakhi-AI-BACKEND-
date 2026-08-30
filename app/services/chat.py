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

from app.services.ai_context.context_builder import HealthContextBuilder, AIHealthContext
from app.db.session import get_session_factory



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

        # 3. Gather Context and RAG evidence
        context = None
        rag_evidence = []
        try:
            SessionLocal = get_session_factory()
            with SessionLocal() as db:
                builder = HealthContextBuilder(db, user_id)
                context = builder.build_context(scopes=["LONGITUDINAL", "SYMPTOMS", "PROFILE"])
                
                from app.services.rag.retrieval import MedicalKnowledgeService
                rag_service = MedicalKnowledgeService(db)
                rag_evidence = rag_service.search(message, limit=3)
        except Exception as e:
            import logging
            logging.error(f"Error fetching context/RAG: {e}")

        # 4. Format Prompt and Generate Response
        from app.services.ai_providers import get_provider
        
        system_prompt = "You are Sakhi, a compassionate women's health AI assistant. "
        if context:
            system_prompt += f"User context: {context.model_dump_json(exclude_none=True)}. "
            
        if rag_evidence:
            system_prompt += "Here is some retrieved medical knowledge to use (cite it if relevant):\n"
            for ev in rag_evidence:
                system_prompt += f"- {ev.content} (Source: {ev.citation.source})\n"
                
        provider = get_provider()
        reply_content = provider.generate_reply(
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": message}] # For a full implementation, we'd fetch actual history
        )

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
