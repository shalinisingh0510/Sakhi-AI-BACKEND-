from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventType = Literal[
    "lesson_view",
    "lesson_complete",
    "lesson_start",
    "conversation_start",
    "conversation_message",
    "profile_update",
    "login",
    "registration",
    "notification_view",
    "notification_click",
]


class AnalyticsEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    event_type: EventType
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime


class CreateEventRequest(BaseModel):
    event_type: EventType
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def normalize_event_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        valid_types = {
            "lesson_view",
            "lesson_complete",
            "lesson_start",
            "conversation_start",
            "conversation_message",
            "profile_update",
            "login",
            "registration",
            "notification_view",
            "notification_click",
        }
        if normalized not in valid_types:
            raise ValueError("Unsupported event type.")
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


class UserEngagementMetrics(BaseModel):
    user_id: str
    total_events: int
    lesson_views: int
    lesson_completions: int
    lesson_starts: int
    conversations_started: int
    messages_sent: int
    profile_updates: int
    logins: int
    last_activity: datetime | None


class PlatformOverview(BaseModel):
    total_users: int
    total_events: int
    active_users_last_7_days: int
    active_users_last_30_days: int
    total_lesson_views: int
    total_lesson_completions: int
    total_conversations: int
    total_messages: int


class EventBreakdown(BaseModel):
    event_type: str
    count: int
    percentage: float


class DailyActivity(BaseModel):
    date: str
    event_count: int
    unique_users: int


class AnalyticsReport(BaseModel):
    overview: PlatformOverview
    event_breakdown: list[EventBreakdown]
    daily_activity: list[DailyActivity]
    top_users_by_engagement: list[UserEngagementMetrics]
