from __future__ import annotations

from app.core.config import Settings
from app.schemas.lesson import LessonSummary
from app.schemas.progress import LessonProgressItem, ProgressOverview, ProgressStatus
from app.services.lessons import LessonService
from app.services.notifications import NotificationService

# This module is intentionally small to avoid circular imports.
# The actual service logic is implemented in the store-backed classes.

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

DEFAULT_PROGRESS_PERCENT = 0
IN_PROGRESS_DEFAULT_PERCENT = 50
COMPLETED_PROGRESS_PERCENT = 100


class ProgressError(Exception):
    """Base exception for lesson progress failures."""


class ProgressNotFoundError(ProgressError):
    pass


class InvalidProgressError(ProgressError):
    pass


@dataclass(slots=True)
class StoredLessonProgress:
    id: str
    user_id: str
    lesson_id: str
    status: str
    progress_percent: int
    notes: str | None
    started_at: datetime
    completed_at: datetime | None
    updated_at: datetime


class ProgressStoreProtocol(Protocol):
    def upsert_progress(
        self,
        *,
        user_id: str,
        lesson_id: str,
        status: str,
        progress_percent: int,
        notes: str | None = None,
    ) -> StoredLessonProgress:
        ...

    def get_progress(self, *, user_id: str, lesson_id: str) -> StoredLessonProgress | None:
        ...

    def list_progress(self, *, user_id: str) -> list[StoredLessonProgress]:
        ...


class ProgressService:
    def __init__(
        self,
        settings: Settings,
        store: ProgressStoreProtocol,
        lesson_service: LessonService,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._lesson_service = lesson_service
        self._notification_service = notification_service

    def list_progress(self, *, user_id: str) -> list[LessonProgressItem]:
        records = self._store.list_progress(user_id=user_id)
        return [self._to_item(record) for record in records]

    def get_progress(self, *, user_id: str, lesson_slug: str) -> LessonProgressItem:
        lesson = self._lesson_service.get_lesson(slug=lesson_slug, published_only=False)
        record = self._store.get_progress(user_id=user_id, lesson_id=lesson.id)
        if record is None:
            raise ProgressNotFoundError("Progress not found for this lesson.")
        return self._to_item(record)

    def upsert_progress(
        self,
        *,
        user_id: str,
        lesson_slug: str,
        status: ProgressStatus,
        progress_percent: int | None = None,
        notes: str | None = None,
    ) -> LessonProgressItem:
        lesson = self._lesson_service.get_lesson(slug=lesson_slug, published_only=False)
        existing_record = self._store.get_progress(user_id=user_id, lesson_id=lesson.id)
        normalized_status = self._normalize_status(status)
        normalized_progress = self._normalize_progress_percent(normalized_status, progress_percent)
        normalized_notes = notes.strip() if notes is not None else None
        if normalized_notes == "":
            normalized_notes = None

        record = self._store.upsert_progress(
            user_id=user_id,
            lesson_id=lesson.id,
            status=normalized_status,
            progress_percent=normalized_progress,
            notes=normalized_notes,
        )

        if (
            self._notification_service is not None
            and normalized_status == "completed"
            and (existing_record is None or existing_record.status != "completed")
        ):
            self._notification_service.create_lesson_completion_notification(
                user_id=user_id,
                lesson_title=lesson.title,
                lesson_slug=lesson.slug,
            )

        return self._to_item(record)

    def summarize_progress(self, *, user_id: str) -> ProgressOverview:
        records = self._store.list_progress(user_id=user_id)
        total_lessons = len(records)
        completed_lessons = sum(1 for record in records if record.status == "completed")
        in_progress_lessons = sum(1 for record in records if record.status == "in_progress")
        not_started_lessons = sum(1 for record in records if record.status == "not_started")
        average_progress_percent = round(sum(record.progress_percent for record in records) / total_lessons, 1) if total_lessons else 0.0
        completion_rate = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0.0
        return ProgressOverview(
            total_lessons=total_lessons,
            completed_lessons=completed_lessons,
            in_progress_lessons=in_progress_lessons,
            not_started_lessons=not_started_lessons,
            completion_rate=completion_rate,
            average_progress_percent=average_progress_percent,
        )

    def _to_item(self, record: StoredLessonProgress) -> LessonProgressItem:
        lesson_detail = self._lesson_service.get_lesson_by_id(record.lesson_id)
        lesson = LessonSummary.model_validate(lesson_detail.model_dump())
        return LessonProgressItem(
            id=record.id,
            lesson_id=record.lesson_id,
            lesson=lesson,
            status=record.status,
            progress_percent=record.progress_percent,
            notes=record.notes,
            started_at=record.started_at,
            completed_at=record.completed_at,
            updated_at=record.updated_at,
        )

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in {"not_started", "in_progress", "completed"}:
            raise InvalidProgressError("Unsupported progress status.")
        return normalized

    def _normalize_progress_percent(self, status: str, progress_percent: int | None) -> int:
        if status == "completed":
            return COMPLETED_PROGRESS_PERCENT
        if status == "not_started":
            return DEFAULT_PROGRESS_PERCENT
        if progress_percent is None:
            return IN_PROGRESS_DEFAULT_PERCENT
        return progress_percent
