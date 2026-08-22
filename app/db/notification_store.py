from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import psycopg

from app.services.notifications import NotificationNotFoundError, StoredNotification


class PostgresNotificationStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    is_read INT NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)")

    def _row_to_notification(self, row: dict) -> StoredNotification:
        created_at = datetime.fromisoformat(row["created_at"])
        read_at = datetime.fromisoformat(row["read_at"]) if row["read_at"] else None
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if read_at is not None and read_at.tzinfo is None:
            read_at = read_at.replace(tzinfo=timezone.utc)

        return StoredNotification(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            body=row["body"],
            notification_type=row["notification_type"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            is_read=bool(row["is_read"]),
            created_at=created_at,
            read_at=read_at,
        )

    def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        notification_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredNotification:
        notification_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO notifications (
                        id, user_id, title, body, notification_type, metadata_json, is_read, created_at, read_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, NULL)
                    """,
                    (
                        notification_id,
                        user_id,
                        title,
                        body,
                        notification_type,
                        json.dumps(metadata or {}),
                        timestamp,
                    ),
                )
        except psycopg.IntegrityError as exc:
            raise RuntimeError("Notification could not be created.") from exc

        notification = self.get_notification(notification_id=notification_id, user_id=user_id)
        if notification is None:
            raise RuntimeError("Stored notification could not be loaded after insertion.")
        return notification

    def list_notifications(self, *, user_id: str, unread_only: bool = False) -> list[StoredNotification]:
        query = "SELECT * FROM notifications WHERE user_id = %s"
        params: list[object] = [user_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(query, params).fetchall()
        return [self._row_to_notification(row) for row in rows]

    def count_unread(self, *, user_id: str) -> int:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT COUNT(*) AS count FROM notifications WHERE user_id = %s AND is_read = 0",
                    (user_id,),
                ).fetchone()
        return int(row["count"])

    def get_notification(self, *, notification_id: str, user_id: str) -> StoredNotification | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT * FROM notifications WHERE id = %s AND user_id = %s",
                    (notification_id, user_id),
                ).fetchone()
        return None if row is None else self._row_to_notification(row)

    def mark_as_read(self, *, notification_id: str, user_id: str) -> StoredNotification:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE notifications
                SET is_read = 1, read_at = %s
                WHERE id = %s AND user_id = %s
                """,
                (timestamp, notification_id, user_id),
            )
        if cursor.rowcount == 0:
            raise NotificationNotFoundError("Notification not found.")

        notification = self.get_notification(notification_id=notification_id, user_id=user_id)
        if notification is None:
            raise NotificationNotFoundError("Notification not found.")
        return notification

    def mark_all_as_read(self, *, user_id: str) -> int:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE notifications SET is_read = 1, read_at = %s WHERE user_id = %s AND is_read = 0",
                (timestamp, user_id),
            )
        return cursor.rowcount

    def delete_notification(self, *, notification_id: str, user_id: str) -> None:
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notifications WHERE id = %s AND user_id = %s",
                (notification_id, user_id),
            )
        if cursor.rowcount == 0:
            raise NotificationNotFoundError("Notification not found.")
