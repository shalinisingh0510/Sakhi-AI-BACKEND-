from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FeedbackCategory = Literal["bug", "feature_request", "content_issue", "general"]
FeedbackStatus = Literal["open", "in_review", "resolved"]


class FeedbackItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    category: FeedbackCategory
    subject: str
    message: str
    rating: int | None = None
    status: FeedbackStatus
    admin_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class FeedbackOverview(BaseModel):
    total_feedback: int
    open_feedback: int
    in_review_feedback: int
    resolved_feedback: int
    average_rating: float | None = None


class SubmitFeedbackRequest(BaseModel):
    category: FeedbackCategory = "general"
    subject: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=10, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"bug", "feature_request", "content_issue", "general"}:
            raise ValueError("Unsupported feedback category.")
        return normalized

    @field_validator("subject", "message")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized


class UpdateFeedbackStatusRequest(BaseModel):
    status: FeedbackStatus
    admin_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"open", "in_review", "resolved"}:
            raise ValueError("Unsupported feedback status.")
        return normalized

    @field_validator("admin_notes")
    @classmethod
    def normalize_admin_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
