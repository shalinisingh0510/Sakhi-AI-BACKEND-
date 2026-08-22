from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import psycopg

from app.services.feedback import StoredFeedback


class PostgresFeedbackStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    rating INTEGER,
                    status TEXT NOT NULL DEFAULT 'open',
                    admin_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at)")

    def _row_to_feedback(self, row: dict) -> StoredFeedback:
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        resolved_at = datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if resolved_at is not None and resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)

        return StoredFeedback(
            id=row["id"],
            user_id=row["user_id"],
            category=row["category"],
            subject=row["subject"],
            message=row["message"],
            rating=int(row["rating"]) if row["rating"] is not None else None,
            status=row["status"],
            admin_notes=row["admin_notes"],
            created_at=created_at,
            updated_at=updated_at,
            resolved_at=resolved_at,
        )

    def create_feedback(
        self,
        *,
        user_id: str,
        category: str,
        subject: str,
        message: str,
        rating: int | None = None,
    ) -> StoredFeedback:
        feedback_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO feedback (
                        id, user_id, category, subject, message, rating, status,
                        admin_notes, created_at, updated_at, resolved_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'open', NULL, %s, %s, NULL)
                    """,
                    (feedback_id, user_id, category, subject, message, rating, timestamp, timestamp),
                )
        except psycopg.IntegrityError as exc:
            raise RuntimeError("Feedback could not be created.") from exc

        feedback = self.get_feedback(feedback_id)
        if feedback is None:
            raise RuntimeError("Stored feedback could not be loaded after insertion.")
        return feedback

    def get_feedback(self, feedback_id: str) -> StoredFeedback | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute("SELECT * FROM feedback WHERE id = %s", (feedback_id,)).fetchone()
        return None if row is None else self._row_to_feedback(row)

    def _build_filters(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> tuple[str, list[object]]:
        conditions: list[str] = []
        params: list[object] = []
        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        if category is not None:
            conditions.append("category = %s")
            params.append(category)
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params

    def list_feedback(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredFeedback]:
        where_clause, params = self._build_filters(user_id=user_id, status=status, category=category)
        query = f"SELECT * FROM feedback{where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(query, params).fetchall()
        return [self._row_to_feedback(row) for row in rows]

    def count_feedback(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> int:
        where_clause, params = self._build_filters(user_id=user_id, status=status, category=category)
        query = f"SELECT COUNT(*) AS count FROM feedback{where_clause}"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(query, params).fetchone()
        return int(row["count"])

    def get_average_rating(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> float | None:
        conditions = ["rating IS NOT NULL"]
        params: list[object] = []
        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        if category is not None:
            conditions.append("category = %s")
            params.append(category)
        query = "SELECT AVG(rating) AS average_rating FROM feedback WHERE " + " AND ".join(conditions)
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(query, params).fetchone()
        return None if row is None or row["average_rating"] is None else float(row["average_rating"])

    def update_feedback_status(
        self,
        *,
        feedback_id: str,
        status: str,
        admin_notes: str | None = None,
    ) -> StoredFeedback:
        existing = self.get_feedback(feedback_id)
        if existing is None:
            raise RuntimeError("Feedback not found.")

        normalized_status = status.strip().lower()
        resolved_at = datetime.now(timezone.utc).isoformat() if normalized_status == "resolved" else None
        notes_value = existing.admin_notes if admin_notes is None else admin_notes.strip() or None
        updated_at = datetime.now(timezone.utc).isoformat()

        with self._pool.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE feedback
                SET status = %s, admin_notes = %s, updated_at = %s, resolved_at = %s
                WHERE id = %s
                """,
                (normalized_status, notes_value, updated_at, resolved_at, feedback_id),
            )
        if cursor.rowcount == 0:
            raise RuntimeError("Feedback not found.")

        feedback = self.get_feedback(feedback_id)
        if feedback is None:
            raise RuntimeError("Feedback not found.")
        return feedback
