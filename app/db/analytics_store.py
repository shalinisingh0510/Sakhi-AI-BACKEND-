from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.services.analytics import StoredAnalyticsEvent


class SQLiteAnalyticsStore:
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
                CREATE TABLE IF NOT EXISTS analytics_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics_events(user_id)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type)")
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at)")

    def _row_to_event(self, row: sqlite3.Row) -> StoredAnalyticsEvent:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return StoredAnalyticsEvent(
            id=row["id"],
            user_id=row["user_id"],
            event_type=row["event_type"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=created_at,
        )

    def create_event(
        self,
        *,
        user_id: str,
        event_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredAnalyticsEvent:
        event_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO analytics_events (id, user_id, event_type, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        user_id,
                        event_type,
                        json.dumps(metadata or {}),
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise RuntimeError("Analytics event could not be created.") from exc

        event = self.get_event(event_id=event_id)
        if event is None:
            raise RuntimeError("Stored analytics event could not be loaded after insertion.")
        return event

    def get_event(self, *, event_id: str) -> StoredAnalyticsEvent | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM analytics_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return None if row is None else self._row_to_event(row)

    def list_user_events(
        self,
        *,
        user_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[StoredAnalyticsEvent]:
        query = "SELECT * FROM analytics_events WHERE user_id = ?"
        params: list[object] = [user_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def count_user_events(self, *, user_id: str, event_type: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM analytics_events WHERE user_id = ?"
        params: list[object] = [user_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        with self._lock:
            row = self._connection.execute(query, params).fetchone()
        return int(row["count"])

    def get_user_engagement_metrics(self, *, user_id: str) -> dict[str, int | datetime | None]:
        with self._lock:
            total_events_row = self._connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            total_events = int(total_events_row["count"])

            lesson_views = self.count_user_events(user_id=user_id, event_type="lesson_view")
            lesson_completions = self.count_user_events(user_id=user_id, event_type="lesson_complete")
            lesson_starts = self.count_user_events(user_id=user_id, event_type="lesson_start")
            conversations_started = self.count_user_events(user_id=user_id, event_type="conversation_start")
            messages_sent = self.count_user_events(user_id=user_id, event_type="conversation_message")
            profile_updates = self.count_user_events(user_id=user_id, event_type="profile_update")
            logins = self.count_user_events(user_id=user_id, event_type="login")

            last_activity_row = self._connection.execute(
                "SELECT created_at FROM analytics_events WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            last_activity = None
            if last_activity_row:
                last_activity = datetime.fromisoformat(last_activity_row["created_at"])
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)

        return {
            "total_events": total_events,
            "lesson_views": lesson_views,
            "lesson_completions": lesson_completions,
            "lesson_starts": lesson_starts,
            "conversations_started": conversations_started,
            "messages_sent": messages_sent,
            "profile_updates": profile_updates,
            "logins": logins,
            "last_activity": last_activity,
        }

    def get_platform_overview(self) -> dict[str, int]:
        with self._lock:
            total_users_row = self._connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            total_users = int(total_users_row["count"])

            total_events_row = self._connection.execute("SELECT COUNT(*) AS count FROM analytics_events").fetchone()
            total_events = int(total_events_row["count"])

            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            active_7_days_row = self._connection.execute(
                "SELECT COUNT(DISTINCT user_id) AS count FROM analytics_events WHERE created_at >= ?",
                (seven_days_ago,),
            ).fetchone()
            active_users_7_days = int(active_7_days_row["count"])

            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            active_30_days_row = self._connection.execute(
                "SELECT COUNT(DISTINCT user_id) AS count FROM analytics_events WHERE created_at >= ?",
                (thirty_days_ago,),
            ).fetchone()
            active_users_30_days = int(active_30_days_row["count"])

            total_lesson_views = self._connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events WHERE event_type = 'lesson_view'"
            ).fetchone()
            total_lesson_views = int(total_lesson_views["count"])

            total_lesson_completions = self._connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events WHERE event_type = 'lesson_complete'"
            ).fetchone()
            total_lesson_completions = int(total_lesson_completions["count"])

            total_conversations = self._connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events WHERE event_type = 'conversation_start'"
            ).fetchone()
            total_conversations = int(total_conversations["count"])

            total_messages = self._connection.execute(
                "SELECT COUNT(*) AS count FROM analytics_events WHERE event_type = 'conversation_message'"
            ).fetchone()
            total_messages = int(total_messages["count"])

        return {
            "total_users": total_users,
            "total_events": total_events,
            "active_users_last_7_days": active_users_7_days,
            "active_users_last_30_days": active_users_30_days,
            "total_lesson_views": total_lesson_views,
            "total_lesson_completions": total_lesson_completions,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
        }

    def get_event_breakdown(self) -> list[dict[str, int | float]]:
        with self._lock:
            total_events_row = self._connection.execute("SELECT COUNT(*) AS count FROM analytics_events").fetchone()
            total_events = int(total_events_row["count"])

            if total_events == 0:
                return []

            rows = self._connection.execute(
                """
                SELECT event_type, COUNT(*) AS count
                FROM analytics_events
                GROUP BY event_type
                ORDER BY count DESC
                """
            ).fetchall()

        breakdown = []
        for row in rows:
            breakdown.append({
                "event_type": row["event_type"],
                "count": int(row["count"]),
                "percentage": round((int(row["count"]) / total_events) * 100, 2),
            })

        return breakdown

    def get_daily_activity(self, days: int = 30) -> list[dict[str, int]]:
        with self._lock:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            rows = self._connection.execute(
                """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM analytics_events
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                (start_date.isoformat(),),
            ).fetchall()

        activity = []
        for row in rows:
            activity.append({
                "date": row["date"],
                "event_count": int(row["event_count"]),
                "unique_users": int(row["unique_users"]),
            })

        return activity

    def get_top_users_by_engagement(self, limit: int = 10) -> list[dict[str, int]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT 
                    user_id,
                    COUNT(*) as total_events,
                    MAX(created_at) as last_activity
                FROM analytics_events
                GROUP BY user_id
                ORDER BY total_events DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        top_users = []
        for row in rows:
            last_activity = datetime.fromisoformat(row["last_activity"])
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)

            top_users.append({
                "user_id": row["user_id"],
                "total_events": int(row["total_events"]),
                "last_activity": last_activity,
            })

        return top_users
