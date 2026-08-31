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
    citations: list[dict] | None = None

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

    def add_message(self, *, conversation_id: str, role: str, content: str, citations: list[dict] | None = None) -> StoredConversationMessage:
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

    def _generate_orchestrated_reply(
        self,
        user_message: str,
        conversation_title: str,
        preferred_language: str,
        history: list[dict[str, str]],
        mode: str = "text",
        health_context: dict | None = None,
    ) -> StructuredAIResponse:
        from app.services.ai_orchestration.safety import HealthSafetyRouter, HealthAIResponseGuard, SafetyRiskLevel
        from app.services.rag.retrieval import MedicalKnowledgeService
        from app.services.ai_orchestration.context_builder import ContextBuilder
        from app.db.session import get_session_factory
        from app.schemas.ai import StructuredAIResponse

        router = HealthSafetyRouter()
        
        # 1. Pre-generation validation
        # Extract age from health context safely.
        user_age = None
        if health_context:
            try:
                if "age" in health_context and health_context["age"] is not None:
                    user_age = int(health_context["age"])
                elif "profile" in health_context and health_context["profile"] and health_context["profile"].get("age") is not None:
                    user_age = int(health_context["profile"]["age"])
            except (ValueError, TypeError):
                pass

        safety_result = router.validate_pre_generation(user_message, user_age)
        if not safety_result.is_safe:
            return StructuredAIResponse(answer=safety_result.override_message, citations=[])

        # 2. RAG Retrieval
        retrieved_context = None
        start_time = __import__("time").time()
        retrieval_result = None
        try:
            db = get_session_factory()()
            try:
                rag_service = MedicalKnowledgeService(db=db)
                retrieval_result = rag_service.search(query=user_message, history=[])
                if retrieval_result.matched_chunks:
                    retrieved_context = ContextBuilder.build_context(
                        chunks=retrieval_result.matched_chunks,
                        compressed_evidence=retrieval_result.synthesized_facts
                    )
            finally:
                db.close()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"RAG search failed: {e}")
        finally:
            # Track analytics (hardcoded event logging for now without heavy refactor)
            try:
                latency = __import__("time").time() - start_time
                chunks_returned = len(retrieval_result.matched_chunks) if retrieval_result and retrieval_result.matched_chunks else 0
                import psycopg
                from app.core.config import get_settings
                with psycopg.connect(get_settings().database_url) as conn:
                    with conn.cursor() as cur:
                        import uuid, json, datetime
                        cur.execute(
                            "INSERT INTO analytics_events (id, user_id, event_type, metadata_json, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (uuid.uuid4().hex, "system", "rag_query", json.dumps({"latency": latency, "chunks_returned": chunks_returned}), datetime.datetime.now(datetime.timezone.utc).isoformat())
                        )
                    conn.commit()
            except Exception as ex:
                import logging
                logging.getLogger(__name__).warning(f"Failed to track RAG analytics: {ex}")

        # 3. LLM Generation
        reply_response = self._provider.generate_reply(
            user_message=user_message,
            conversation_title=conversation_title,
            preferred_language=preferred_language,
            history=history,
            mode=mode,
            health_context=health_context,
            retrieved_context=retrieved_context
        )

        # 4. Post-generation validation
        guard = HealthAIResponseGuard()
        if not guard.validate_post_generation(reply_response.answer):
            return StructuredAIResponse(
                answer="I apologize, but I am unable to provide a safe response to that question. Please consult a healthcare professional for medical advice.",
                citations=[]
            )

        return reply_response

    def create_conversation(
        self,
        *,
        user_id: str,
        title: str | None,
        initial_message: str,
        preferred_language: str | None = None,
        mode: str = "text",
        health_context: dict | None = None,
    ) -> ConversationDetail:
        language = self._normalize_language(preferred_language)
        conversation_title = self._normalize_title(title, initial_message)
        conversation = self._store.create_conversation(
            user_id=user_id,
            title=conversation_title,
            preferred_language=language,
        )
        self._store.add_message(conversation_id=conversation.id, role="user", content=initial_message)
        
        reply_response = self._generate_orchestrated_reply(
            user_message=initial_message,
            conversation_title=conversation.title,
            preferred_language=conversation.preferred_language,
            history=[],
            mode=mode,
            health_context=health_context
        )
        
        self._store.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply_response.answer,
            citations=[c.model_dump(exclude_none=True) for c in reply_response.citations],
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
        mode: str = "text",
        health_context: dict | None = None,
    ) -> ConversationDetail:
        conversation = self._require_owned_conversation(user_id=user_id, conversation_id=conversation_id)
        self._store.add_message(conversation_id=conversation.id, role="user", content=message)
        # Build recent history for context-aware replies (respects history limit)
        history = self._build_history(conversation_id=conversation.id, exclude_last_n=1)
        
        reply_response = self._generate_orchestrated_reply(
            user_message=message,
            conversation_title=conversation.title,
            preferred_language=conversation.preferred_language,
            history=history,
            mode=mode,
            health_context=health_context
        )
        
        self._store.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=reply_response.answer,
            citations=[c.model_dump(exclude_none=True) for c in reply_response.citations],
        )
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

