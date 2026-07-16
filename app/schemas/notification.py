from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NotificationType = Literal["announcement", "lesson_completed", "reminder", "system"]


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    body: str
    notification_type: NotificationType
    metadata: dict[str, str] = Field(default_factory=dict)
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationDispatchResult(BaseModel):
    created_count: int
    notifications: list[NotificationItem]


class CreateNotificationRequest(BaseModel):
    recipient_user_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=2, max_length=140)
    body: str = Field(min_length=5, max_length=2000)
    notification_type: NotificationType = "announcement"
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("recipient_user_id")
    @classmethod
    def normalize_recipient_user_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("title", "body")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized

    @field_validator("notification_type")
    @classmethod
    def normalize_notification_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"announcement", "lesson_completed", "reminder", "system"}:
            raise ValueError("Unsupported notification type.")
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            normalized: dict[str, str] = {}
            for key, item in value.items():
                normalized_key = str(key).strip()
                if not normalized_key:
                    continue
                normalized[normalized_key] = str(item).strip()
            return normalized
        return {}
