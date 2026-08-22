from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.config import Settings
from app.services.storage import StorageServiceProtocol

logger = logging.getLogger(__name__)


@dataclass
class StoredMedia:
    id: str
    uploader_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    created_at: datetime


class MediaStoreProtocol(Protocol):
    def create_media_record(
        self,
        *,
        uploader_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
    ) -> StoredMedia: ...

    def get_media_record(self, media_id: str) -> StoredMedia | None: ...

    def list_user_media(self, uploader_id: str) -> list[StoredMedia]: ...

    def delete_media_record(self, media_id: str) -> None: ...


class MediaNotFoundError(Exception):
    pass


class MediaService:
    def __init__(self, settings: Settings, store: MediaStoreProtocol, storage_service: StorageServiceProtocol) -> None:
        self.settings = settings
        self._store = store
        self._storage_service = storage_service

    def generate_upload_url(self, uploader_id: str, filename: str, content_type: str, size_bytes: int) -> dict[str, str | StoredMedia]:
        import uuid
        import mimetypes

        ext = mimetypes.guess_extension(content_type) or ""
        # Unique storage key to prevent collisions
        storage_key = f"uploads/{uploader_id}/{uuid.uuid4().hex}{ext}"

        # Get presigned URL from storage service
        presigned_url = self._storage_service.generate_presigned_upload_url(storage_key, content_type)

        # Create the database record
        media_record = self._store.create_media_record(
            uploader_id=uploader_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )

        return {
            "upload_url": presigned_url,
            "storage_key": storage_key,
            "media_record": media_record,
        }

    def get_media_url(self, media_id: str) -> str:
        record = self._store.get_media_record(media_id)
        if not record:
            raise MediaNotFoundError(f"Media {media_id} not found.")

        # In a real app, if the bucket is public, this might just be a CDN URL.
        # But if it's private, we generate a presigned download URL.
        return self._storage_service.generate_presigned_download_url(record.storage_key)

    def get_user_media(self, user_id: str) -> list[StoredMedia]:
        return self._store.list_user_media(user_id)
