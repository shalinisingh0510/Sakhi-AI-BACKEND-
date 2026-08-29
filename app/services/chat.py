from __future__ import annotations

from app.schemas.ai import ConversationDetail
from app.services.ai import ConversationNotFoundError, ConversationStoreProtocol, StoredConversation

DEFAULT_CHAT_TITLE = 'Health guidance'
TEMPORARY_CHAT_REPLY = (
    'Thanks, your message reached Sakhi Chat. '
    'This is a temporary backend response while the full assistant is being connected.'
)


class ChatService:
    def __init__(self, store: ConversationStoreProtocol) -> None:
        self._store = store

    def send_message(
        self,
        *,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        preferred_language: str = 'english',
        mode: str = 'text',
    ) -> ConversationDetail:
        conversation = self._resolve_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            initial_message=message,
            preferred_language=preferred_language,
        )

        self._store.add_message(conversation_id=conversation.id, role='user', content=message)
        self._store.add_message(
            conversation_id=conversation.id,
            role='assistant',
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

        title = self._build_conversation_title(initial_message)
        return self._store.create_conversation(
            user_id=user_id,
            title=title,
            preferred_language=preferred_language,
        )

    def _require_owned_conversation(self, *, user_id: str, conversation_id: str) -> StoredConversation:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ConversationNotFoundError('Conversation not found.')
        return conversation

    def _build_conversation_title(self, message: str) -> str:
        snippet = ' '.join(message.strip().split())
        if not snippet:
            return DEFAULT_CHAT_TITLE
        return snippet[:60] if len(snippet) <= 60 else f'{snippet[:57].rstrip()}...'

    def _build_temporary_reply(self, *, mode: str) -> str:
        if mode == 'voice':
            return 'Thanks. Your message reached Sakhi Chat. This is a temporary backend response.'
        return TEMPORARY_CHAT_REPLY
