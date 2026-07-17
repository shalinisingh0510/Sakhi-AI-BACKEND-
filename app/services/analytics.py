from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.core.config import Settings
from app.schemas.analytics import (
    AnalyticsEvent,
    AnalyticsReport,
    DailyActivity,
    EventBreakdown,
    EventType,
    PlatformOverview,
    UserEngagementMetrics,
)


class AnalyticsError(Exception):
    """Base exception for analytics failures."""


class AnalyticsNotFoundError(AnalyticsError):
    pass


@dataclass(slots=True)
class StoredAnalyticsEvent:
    id: str
    user_id: str
    event_type: str
    metadata: dict[str, str]
    created_at: datetime

    def to_event(self) -> AnalyticsEvent:
        return AnalyticsEvent.model_validate(self)


class AnalyticsStoreProtocol(Protocol):
    def create_event(
        self,
        *,
        user_id: str,
        event_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredAnalyticsEvent:
        ...

    def get_event(self, *, event_id: str) -> StoredAnalyticsEvent | None:
        ...

    def list_user_events(
        self,
        *,
        user_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[StoredAnalyticsEvent]:
        ...

    def count_user_events(self, *, user_id: str, event_type: str | None = None) -> int:
        ...

    def get_user_engagement_metrics(self, *, user_id: str) -> dict[str, int | datetime | None]:
        ...

    def get_platform_overview(self) -> dict[str, int]:
        ...

    def get_event_breakdown(self) -> list[dict[str, int | float]]:
        ...

    def get_daily_activity(self, days: int = 30) -> list[dict[str, int]]:
        ...

    def get_top_users_by_engagement(self, limit: int = 10) -> list[dict[str, int]]:
        ...


class AnalyticsService:
    def __init__(self, settings: Settings, store: AnalyticsStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def track_event(
        self,
        *,
        user_id: str,
        event_type: EventType,
        metadata: dict[str, str] | None = None,
    ) -> AnalyticsEvent:
        record = self._store.create_event(
            user_id=user_id,
            event_type=event_type,
            metadata=metadata or {},
        )
        return record.to_event()

    def get_user_events(
        self,
        *,
        user_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AnalyticsEvent]:
        return [event.to_event() for event in self._store.list_user_events(user_id=user_id, event_type=event_type, limit=limit)]

    def get_user_engagement_metrics(self, *, user_id: str) -> UserEngagementMetrics:
        metrics = self._store.get_user_engagement_metrics(user_id=user_id)
        return UserEngagementMetrics(
            user_id=user_id,
            total_events=metrics["total_events"],
            lesson_views=metrics["lesson_views"],
            lesson_completions=metrics["lesson_completions"],
            lesson_starts=metrics["lesson_starts"],
            conversations_started=metrics["conversations_started"],
            messages_sent=metrics["messages_sent"],
            profile_updates=metrics["profile_updates"],
            logins=metrics["logins"],
            last_activity=metrics["last_activity"],
        )

    def get_platform_overview(self) -> PlatformOverview:
        overview = self._store.get_platform_overview()
        return PlatformOverview(
            total_users=overview["total_users"],
            total_events=overview["total_events"],
            active_users_last_7_days=overview["active_users_last_7_days"],
            active_users_last_30_days=overview["active_users_last_30_days"],
            total_lesson_views=overview["total_lesson_views"],
            total_lesson_completions=overview["total_lesson_completions"],
            total_conversations=overview["total_conversations"],
            total_messages=overview["total_messages"],
        )

    def get_event_breakdown(self) -> list[EventBreakdown]:
        breakdown = self._store.get_event_breakdown()
        return [EventBreakdown(
            event_type=item["event_type"],
            count=item["count"],
            percentage=item["percentage"],
        ) for item in breakdown]

    def get_daily_activity(self, days: int = 30) -> list[DailyActivity]:
        activity = self._store.get_daily_activity(days=days)
        return [DailyActivity(
            date=item["date"],
            event_count=item["event_count"],
            unique_users=item["unique_users"],
        ) for item in activity]

    def get_top_users_by_engagement(self, limit: int = 10) -> list[UserEngagementMetrics]:
        top_users = self._store.get_top_users_by_engagement(limit=limit)
        metrics_list = []
        for user_data in top_users:
            full_metrics = self._store.get_user_engagement_metrics(user_id=user_data["user_id"])
            metrics_list.append(UserEngagementMetrics(
                user_id=user_data["user_id"],
                total_events=user_data["total_events"],
                lesson_views=full_metrics["lesson_views"],
                lesson_completions=full_metrics["lesson_completions"],
                lesson_starts=full_metrics["lesson_starts"],
                conversations_started=full_metrics["conversations_started"],
                messages_sent=full_metrics["messages_sent"],
                profile_updates=full_metrics["profile_updates"],
                logins=full_metrics["logins"],
                last_activity=user_data["last_activity"],
            ))
        return metrics_list

    def generate_analytics_report(self) -> AnalyticsReport:
        return AnalyticsReport(
            overview=self.get_platform_overview(),
            event_breakdown=self.get_event_breakdown(),
            daily_activity=self.get_daily_activity(days=30),
            top_users_by_engagement=self.get_top_users_by_engagement(limit=10),
        )
