from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.services.media import StoredMedia

logger = logging.getLogger(__name__)


class PostgresMediaStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_files (
                    id TEXT PRIMARY KEY,
                    uploader_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes INT NOT NULL,
                    storage_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(uploader_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_uploader_id ON media_files(uploader_id)")

    def _row_to_media(self, row: dict) -> StoredMedia:
        created_at = datetime.fromisoformat(row["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return StoredMedia(
            id=row["id"],
            uploader_id=row["uploader_id"],
            filename=row["filename"],
            content_type=row["content_type"],
            size_bytes=int(row["size_bytes"]),
            storage_key=row["storage_key"],
            created_at=created_at,
        )

    def create_media_record(
        self,
        *,
        uploader_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
    ) -> StoredMedia:
        media_id = uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO media_files (id, uploader_id, filename, content_type, size_bytes, storage_key, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (media_id, uploader_id, filename, content_type, size_bytes, storage_key, timestamp),
                )
        except psycopg.IntegrityError as exc:
            raise RuntimeError("Media record could not be created. Storage key might not be unique.") from exc

        record = self.get_media_record(media_id)
        if record is None:
            raise RuntimeError("Stored media could not be loaded after insertion.")
        return record

    def get_media_record(self, media_id: str) -> StoredMedia | None:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                row = cursor.execute(
                    "SELECT * FROM media_files WHERE id = %s",
                    (media_id,),
                ).fetchone()
        return None if row is None else self._row_to_media(row)

    def list_user_media(self, uploader_id: str) -> list[StoredMedia]:
        with self._pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                rows = cursor.execute(
                    "SELECT * FROM media_files WHERE uploader_id = %s ORDER BY created_at DESC",
                    (uploader_id,),
                ).fetchall()
        return [self._row_to_media(row) for row in rows]

    def delete_media_record(self, media_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM media_files WHERE id = %s",
                (media_id,),
            )
