from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.core.config import Settings
from app.schemas.feedback import FeedbackItem, FeedbackOverview

VALID_FEEDBACK_CATEGORIES = {"bug", "feature_request", "content_issue", "general"}
VALID_FEEDBACK_STATUSES = {"open", "in_review", "resolved"}


class FeedbackError(Exception):
    """Base exception for feedback failures."""


class FeedbackNotFoundError(FeedbackError):
    pass


class InvalidFeedbackError(FeedbackError):
    pass


@dataclass(slots=True)
class StoredFeedback:
    id: str
    user_id: str
    category: str
    subject: str
    message: str
    rating: int | None
    status: str
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    def to_item(self) -> FeedbackItem:
        return FeedbackItem.model_validate(self)


class FeedbackStoreProtocol(Protocol):
    def create_feedback(
        self,
        *,
        user_id: str,
        category: str,
        subject: str,
        message: str,
        rating: int | None = None,
    ) -> StoredFeedback:
        ...

    def get_feedback(self, feedback_id: str) -> StoredFeedback | None:
        ...

    def list_feedback(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoredFeedback]:
        ...

    def count_feedback(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> int:
        ...

    def get_average_rating(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> float | None:
        ...

    def update_feedback_status(
        self,
        *,
        feedback_id: str,
        status: str,
        admin_notes: str | None = None,
    ) -> StoredFeedback:
        ...


class FeedbackService:
    def __init__(self, settings: Settings, store: FeedbackStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def submit_feedback(
        self,
        *,
        user_id: str,
        category: str,
        subject: str,
        message: str,
        rating: int | None = None,
    ) -> FeedbackItem:
        normalized_category = self._normalize_category(category)
        normalized_subject = subject.strip()
        normalized_message = message.strip()
        normalized_rating = self._normalize_rating(rating)
        record = self._store.create_feedback(
            user_id=user_id,
            category=normalized_category,
            subject=normalized_subject,
            message=normalized_message,
            rating=normalized_rating,
        )
        return record.to_item()

    def list_feedback(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeedbackItem]:
        normalized_status = self._normalize_optional_status(status)
        normalized_category = self._normalize_optional_category(category)
        records = self._store.list_feedback(
            user_id=user_id,
            status=normalized_status,
            category=normalized_category,
            limit=limit,
            offset=offset,
        )
        return [record.to_item() for record in records]

    def get_feedback(self, *, feedback_id: str) -> FeedbackItem:
        record = self._store.get_feedback(feedback_id)
        if record is None:
            raise FeedbackNotFoundError("Feedback not found.")
        return record.to_item()

    def update_feedback_status(
        self,
        *,
        feedback_id: str,
        status: str,
        admin_notes: str | None = None,
    ) -> FeedbackItem:
        normalized_status = self._normalize_status(status)
        normalized_notes = None if admin_notes is None else admin_notes.strip()
        if normalized_notes == "":
            normalized_notes = None
        try:
            record = self._store.update_feedback_status(
                feedback_id=feedback_id,
                status=normalized_status,
                admin_notes=normalized_notes,
            )
        except RuntimeError as exc:
            raise FeedbackNotFoundError(str(exc)) from exc
        return record.to_item()

    def get_overview(self) -> FeedbackOverview:
        total = self._store.count_feedback()
        open_count = self._store.count_feedback(status="open")
        in_review_count = self._store.count_feedback(status="in_review")
        resolved_count = self._store.count_feedback(status="resolved")
        average_rating = self._store.get_average_rating()
        return FeedbackOverview(
            total_feedback=total,
            open_feedback=open_count,
            in_review_feedback=in_review_count,
            resolved_feedback=resolved_count,
            average_rating=round(average_rating, 1) if average_rating is not None else None,
        )

    def _normalize_category(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_FEEDBACK_CATEGORIES:
            raise InvalidFeedbackError("Unsupported feedback category.")
        return normalized

    def _normalize_optional_category(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._normalize_category(value)

    def _normalize_status(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_FEEDBACK_STATUSES:
            raise InvalidFeedbackError("Unsupported feedback status.")
        return normalized

    def _normalize_optional_status(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._normalize_status(value)

    def _normalize_rating(self, value: int | None) -> int | None:
        if value is None:
            return None
        if not 1 <= int(value) <= 5:
            raise InvalidFeedbackError("Rating must be between 1 and 5.")
        return int(value)
