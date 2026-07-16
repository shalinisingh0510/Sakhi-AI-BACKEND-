from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.services.progress import StoredLessonProgress


class SQLiteProgressStore:
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
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_percent INTEGER NOT NULL,
                    notes TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, lesson_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id ON lesson_progress(user_id)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_lesson_id ON lesson_progress(lesson_id)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_status ON lesson_progress(status)")

    def _row_to_progress(self, row: sqlite3.Row) -> StoredLessonProgress:
        started_at = datetime.fromisoformat(row["started_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if completed_at is not None and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        return StoredLessonProgress(
            id=row["id"],
            user_id=row["user_id"],
            lesson_id=row["lesson_id"],
            status=row["status"],
            progress_percent=int(row["progress_percent"]),
            notes=row["notes"],
            started_at=started_at,
            completed_at=completed_at,
            updated_at=updated_at,
        )

    def upsert_progress(
        self,
        *,
        user_id: str,
        lesson_id: str,
        status: str,
        progress_percent: int,
        notes: str | None = None,
    ) -> StoredLessonProgress:
        progress_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        completed_at = timestamp if status == "completed" else None

        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO lesson_progress (
                    id, user_id, lesson_id, status, progress_percent, notes, started_at, completed_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                    status = excluded.status,
                    progress_percent = excluded.progress_percent,
                    notes = excluded.notes,
                    completed_at = excluded.completed_at,
                    updated_at = excluded.updated_at
                """,
                (
                    progress_id,
                    user_id,
                    lesson_id,
                    status,
                    progress_percent,
                    notes,
                    timestamp,
                    completed_at,
                    timestamp,
                ),
            )

        progress = self.get_progress(user_id=user_id, lesson_id=lesson_id)
        if progress is None:
            raise RuntimeError("Stored lesson progress could not be loaded after insertion.")
        return progress

    def get_progress(self, *, user_id: str, lesson_id: str) -> StoredLessonProgress | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, user_id, lesson_id, status, progress_percent, notes, started_at, completed_at, updated_at
                FROM lesson_progress
                WHERE user_id = ? AND lesson_id = ?
                """,
                (user_id, lesson_id),
            ).fetchone()
        return None if row is None else self._row_to_progress(row)

    def list_progress(self, *, user_id: str) -> list[StoredLessonProgress]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, user_id, lesson_id, status, progress_percent, notes, started_at, completed_at, updated_at
                FROM lesson_progress
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_progress(row) for row in rows]
