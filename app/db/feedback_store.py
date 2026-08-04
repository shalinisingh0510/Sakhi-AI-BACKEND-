from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.services.feedback import StoredFeedback


class SQLiteFeedbackStore:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._lock = RLock()
        self._connection = sqlite3.connect(self._database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
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
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at)")

    def _row_to_feedback(self, row: sqlite3.Row) -> StoredFeedback:
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
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO feedback (
                        id, user_id, category, subject, message, rating, status,
                        admin_notes, created_at, updated_at, resolved_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'open', NULL, ?, ?, NULL)
                    """,
                    (feedback_id, user_id, category, subject, message, rating, timestamp, timestamp),
                )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError("Feedback could not be created.") from exc

        feedback = self.get_feedback(feedback_id)
        if feedback is None:
            raise RuntimeError("Stored feedback could not be loaded after insertion.")
        return feedback

    def get_feedback(self, feedback_id: str) -> StoredFeedback | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
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
            conditions.append("user_id = ?")
            params.append(user_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if category is not None:
            conditions.append("category = ?")
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
        query = f"SELECT * FROM feedback{where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
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
        with self._lock:
            row = self._connection.execute(query, params).fetchone()
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
            conditions.append("user_id = ?")
            params.append(user_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        query = "SELECT AVG(rating) AS average_rating FROM feedback WHERE " + " AND ".join(conditions)
        with self._lock:
            row = self._connection.execute(query, params).fetchone()
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

        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE feedback
                SET status = ?, admin_notes = ?, updated_at = ?, resolved_at = ?
                WHERE id = ?
                """,
                (normalized_status, notes_value, updated_at, resolved_at, feedback_id),
            )
        if cursor.rowcount == 0:
            raise RuntimeError("Feedback not found.")

        feedback = self.get_feedback(feedback_id)
        if feedback is None:
            raise RuntimeError("Feedback not found.")
        return feedback

