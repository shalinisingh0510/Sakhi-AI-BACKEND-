from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import psycopg

from app.services.lessons import DuplicateLessonSlugError, StoredLesson


class PostgresLessonStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()
        self._seed_default_lessons()
        self._rebuild_search_index()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    language TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    sections_json TEXT NOT NULL,
                    translations_json TEXT NOT NULL DEFAULT '{}',
                    published INT NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by_user_id TEXT,
                    is_deleted INT NOT NULL DEFAULT 0,
                    deleted_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_language ON lessons(language)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_published ON lessons(published)")
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lesson_search_index (
                    lesson_id TEXT PRIMARY KEY,
                    search_text TEXT NOT NULL,
                    FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
                """
            )

    def _build_search_text(self, lesson: StoredLesson) -> str:
        return lesson.search_text()

    def _sync_search_index(self, lesson: StoredLesson) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM lesson_search_index WHERE lesson_id = %s", (lesson.id,))
            conn.execute(
                """
                INSERT INTO lesson_search_index (lesson_id, search_text)
                VALUES (%s, %s)
                """,
                (lesson.id, self._build_search_text(lesson)),
            )

    def _delete_search_index(self, lesson_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM lesson_search_index WHERE lesson_id = %s", (lesson_id,))

    def _rebuild_search_index(self) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM lesson_search_index")
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute("SELECT * FROM lessons WHERE is_deleted = 0").fetchall()
            
            for row in rows:
                lesson = self._row_to_lesson(row)
                conn.execute(
                    """
                    INSERT INTO lesson_search_index (lesson_id, search_text)
                    VALUES (%s, %s)
                    """,
                    (lesson.id, self._build_search_text(lesson)),
                )

    def _seed_default_lessons(self) -> None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                count = cursor.execute("SELECT COUNT(*) AS count FROM lessons").fetchone()["count"]
        if count:
            return

        default_lessons = [
            {
                "title": "Understanding Periods",
                "slug": "understanding-periods",
                "category": "menstrual-health",
                "summary": "A gentle introduction to periods, common changes, and when to ask for help.",
                "language": "english",
                "audience": "teens",
                "tags": ["periods", "cycle", "health"],
                "sections": [
                    {
                        "heading": "What is normal?",
                        "body": "Period flow, cramps, and cycle length can vary from person to person. Tracking patterns helps you notice changes.",
                    },
                    {
                        "heading": "When to seek help",
                        "body": "Very heavy bleeding, severe pain, or dizziness are signs to speak with a clinician or trusted adult.",
                    },
                ],
            },
            {
                "title": "Body Hygiene Basics",
                "slug": "body-hygiene-basics",
                "category": "hygiene",
                "summary": "Simple daily habits that support comfort, cleanliness, and confidence.",
                "language": "english",
                "audience": "general",
                "tags": ["hygiene", "self-care", "wellbeing"],
                "sections": [
                    {
                        "heading": "Daily care",
                        "body": "Use gentle products, change clothes after sweating, and keep sensitive areas clean and dry.",
                    },
                    {
                        "heading": "Common mistakes",
                        "body": "Harsh soaps, tight damp clothing, and ignoring irritation can make discomfort worse.",
                    },
                ],
            },
            {
                "title": "Managing Stress and Emotions",
                "slug": "managing-stress-and-emotions",
                "category": "mental-health",
                "summary": "Practical ways to notice stress, breathe, and ask for support when needed.",
                "language": "english",
                "audience": "general",
                "tags": ["stress", "emotions", "support"],
                "sections": [
                    {
                        "heading": "Slow the body",
                        "body": "Breathing slowly and relaxing your shoulders can help your body feel safer in the moment.",
                    },
                    {
                        "heading": "Reach out",
                        "body": "If stress feels heavy or keeps coming back, talk with someone you trust or a qualified professional.",
                    },
                ],
            },
        ]

        for lesson in default_lessons:
            self.create_lesson(
                title=lesson["title"],
                slug=lesson["slug"],
                category=lesson["category"],
                summary=lesson["summary"],
                language=lesson["language"],
                audience=lesson["audience"],
                tags=lesson["tags"],
                sections=lesson["sections"],
                translations={},
                published=True,
            )

    def _row_to_lesson(self, row: dict) -> StoredLesson:
        created_at = datetime.fromisoformat(row["created_at"])
        updated_at = datetime.fromisoformat(row["updated_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        translations_raw = json.loads(row["translations_json"]) if row["translations_json"] else {}

        return StoredLesson(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            category=row["category"],
            summary=row["summary"],
            language=row["language"],
            audience=row["audience"],
            tags=json.loads(row["tags_json"]),
            sections=json.loads(row["sections_json"]),
            translations={str(language).strip().lower(): dict(content) for language, content in translations_raw.items()},
            published=bool(row["published"]),
            created_at=created_at,
            updated_at=updated_at,
            created_by_user_id=row["created_by_user_id"],
        )

    def create_lesson(
        self,
        *,
        title: str,
        slug: str,
        category: str,
        summary: str,
        language: str,
        audience: str,
        tags: list[str],
        sections: list[dict[str, str]],
        translations: dict[str, dict[str, object]],
        published: bool,
        created_by_user_id: str | None = None,
    ) -> StoredLesson:
        lesson_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO lessons (
                        id, slug, title, category, summary, language, audience,
                        tags_json, sections_json, translations_json, published, created_at, updated_at, created_by_user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lesson_id,
                        slug,
                        title,
                        category,
                        summary,
                        language,
                        audience,
                        json.dumps(tags),
                        json.dumps(sections),
                        json.dumps(translations),
                        1 if published else 0,
                        timestamp,
                        timestamp,
                        created_by_user_id,
                    ),
                )
        except psycopg.IntegrityError as exc:
            raise DuplicateLessonSlugError("A lesson already exists for this slug.") from exc

        lesson = self.get_by_id(lesson_id)
        if lesson is None:
            raise RuntimeError("Stored lesson could not be loaded after insertion.")
        self._sync_search_index(lesson)
        return lesson

    def get_by_id(self, lesson_id: str) -> StoredLesson | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT * FROM lessons WHERE id = %s AND is_deleted = 0",
                    (lesson_id,),
                ).fetchone()
        return None if row is None else self._row_to_lesson(row)

    def get_by_slug(self, slug: str) -> StoredLesson | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT * FROM lessons WHERE slug = %s AND is_deleted = 0",
                    (slug.strip().lower(),),
                ).fetchone()
        return None if row is None else self._row_to_lesson(row)

    def list_lessons(self, *, published_only: bool | None = None) -> list[StoredLesson]:
        conditions = ["is_deleted = 0"]
        if published_only is True:
            conditions.append("published = 1")
        query = f"SELECT * FROM lessons WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(query).fetchall()
        return [self._row_to_lesson(row) for row in rows]

    def search_lessons(self, query: str, *, published_only: bool | None = None) -> list[StoredLesson]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return self.list_lessons(published_only=published_only)

        tokens = re.findall(r"[\w]+", normalized_query, flags=re.UNICODE)
        if not tokens:
            return []
        fts_query = " & ".join(f"{token}:*" for token in tokens)

        conditions = ["to_tsvector('english', lesson_search_index.search_text) @@ to_tsquery('english', %s)", "l.is_deleted = 0"]
        params: list[object] = [fts_query]
        if published_only is True:
            conditions.append("l.published = 1")
        query_sql = f"""
            SELECT l.*
            FROM lesson_search_index
            JOIN lessons l ON l.id = lesson_search_index.lesson_id
            WHERE {' AND '.join(conditions)}
            ORDER BY l.updated_at DESC
        """
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(query_sql, params).fetchall()
        return [self._row_to_lesson(row) for row in rows]

    def list_categories(self, *, published_only: bool = True) -> list[tuple[str, int]]:
        conditions = ["is_deleted = 0"]
        if published_only:
            conditions.append("published = 1")
        query = f"SELECT category, COUNT(*) AS count FROM lessons WHERE {' AND '.join(conditions)} GROUP BY category ORDER BY category ASC"
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(query).fetchall()
        return [(row["category"], int(row["count"])) for row in rows]

    def update_lesson(
        self,
        *,
        lesson_id: str,
        title: str | None = None,
        slug: str | None = None,
        category: str | None = None,
        summary: str | None = None,
        language: str | None = None,
        audience: str | None = None,
        tags: list[str] | None = None,
        sections: list[dict[str, str]] | None = None,
        translations: dict[str, dict[str, object]] | None = None,
        published: bool | None = None,
    ) -> StoredLesson:
        updates: list[str] = []
        params: list[object] = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if slug is not None:
            updates.append("slug = %s")
            params.append(slug)
        if category is not None:
            updates.append("category = %s")
            params.append(category)
        if summary is not None:
            updates.append("summary = %s")
            params.append(summary)
        if language is not None:
            updates.append("language = %s")
            params.append(language)
        if audience is not None:
            updates.append("audience = %s")
            params.append(audience)
        if tags is not None:
            updates.append("tags_json = %s")
            params.append(json.dumps(tags))
        if sections is not None:
            updates.append("sections_json = %s")
            params.append(json.dumps(sections))
        if translations is not None:
            updates.append("translations_json = %s")
            params.append(json.dumps(translations))
        if published is not None:
            updates.append("published = %s")
            params.append(1 if published else 0)

        if not updates:
            lesson = self.get_by_id(lesson_id)
            if lesson is None:
                raise RuntimeError("Lesson not found.")
            return lesson

        timestamp = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = %s")
        params.append(timestamp)
        params.append(lesson_id)

        try:
            with self._pool.connection() as conn:
                cursor = conn.execute(
                    f"UPDATE lessons SET {', '.join(updates)} WHERE id = %s AND is_deleted = 0",
                    params,
                )
        except psycopg.IntegrityError as exc:
            raise DuplicateLessonSlugError("A lesson already exists for this slug.") from exc

        if cursor.rowcount == 0:
            raise RuntimeError("Lesson not found.")

        lesson = self.get_by_id(lesson_id)
        if lesson is None:
            raise RuntimeError("Lesson not found.")
        self._sync_search_index(lesson)
        return lesson

    def delete_lesson(self, lesson_id: str) -> None:
        """Soft-delete: mark lesson as deleted rather than removing the row."""
        deleted_at = datetime.now(timezone.utc).isoformat()
        with self._pool.connection() as conn:
            cursor = conn.execute(
                "UPDATE lessons SET is_deleted = 1, deleted_at = %s, published = 0 WHERE id = %s AND is_deleted = 0",
                (deleted_at, lesson_id),
            )
        if cursor.rowcount == 0:
            raise RuntimeError("Lesson not found.")
        
        self._delete_search_index(lesson_id)
