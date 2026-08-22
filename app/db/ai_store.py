from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from app.services.ai import StoredConversation, StoredConversationMessage


class PostgresConversationStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    preferred_language TEXT NOT NULL DEFAULT 'english',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id)")

    def _row_to_conversation(self, row: dict, message_count: int = 0) -> StoredConversation:
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        return StoredConversation(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            preferred_language=row["preferred_language"],
            created_at=created_at,
            updated_at=updated_at,
            message_count=message_count,
        )

    def _row_to_message(self, row: dict) -> StoredConversationMessage:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return StoredConversationMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=created_at,
        )

    def create_conversation(
        self,
        *,
        user_id: str,
        title: str,
        preferred_language: str,
    ) -> StoredConversation:
        conversation_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, user_id, title, preferred_language, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (conversation_id, user_id, title, preferred_language, timestamp, timestamp),
            )
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise RuntimeError("Stored conversation could not be loaded after insertion.")
        return conversation

    def get_conversation(self, conversation_id: str) -> StoredConversation | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT id, user_id, title, preferred_language, created_at, updated_at FROM conversations WHERE id = %s",
                    (conversation_id,),
                ).fetchone()
                if row is None:
                    return None
                message_count = cursor.execute(
                    "SELECT COUNT(*) AS count FROM conversation_messages WHERE conversation_id = %s",
                    (conversation_id,),
                ).fetchone()["count"]
        return self._row_to_conversation(row, int(message_count))

    def list_conversations(self, user_id: str) -> list[StoredConversation]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT c.id, c.user_id, c.title, c.preferred_language, c.created_at, c.updated_at,
                           COUNT(m.id) AS message_count
                    FROM conversations c
                    LEFT JOIN conversation_messages m ON m.conversation_id = c.id
                    WHERE c.user_id = %s
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                    """,
                    (user_id,),
                ).fetchall()
        return [self._row_to_conversation(row, int(row["message_count"])) for row in rows]

    def get_messages(self, conversation_id: str) -> list[StoredConversationMessage]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    """
                    SELECT id, conversation_id, role, content, created_at
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (conversation_id,),
                ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def add_message(self, *, conversation_id: str, role: str, content: str) -> StoredConversationMessage:
        message_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO conversation_messages (id, conversation_id, role, content, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (message_id, conversation_id, role, content, timestamp),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = %s WHERE id = %s",
                (timestamp, conversation_id),
            )
        message = self.get_messages(conversation_id)
        for stored_message in reversed(message):
            if stored_message.id == message_id:
                return stored_message
        raise RuntimeError("Stored conversation message could not be loaded after insertion.")

    def update_conversation_timestamp(self, conversation_id: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE conversations SET updated_at = %s WHERE id = %s",
                (timestamp, conversation_id),
            )
        if cursor.rowcount == 0:
            raise RuntimeError("Conversation could not be updated.")
