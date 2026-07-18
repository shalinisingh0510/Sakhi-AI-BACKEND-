from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Protocol

from app.core.cache import CacheBackendProtocol, build_cache_key
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
    def __init__(self, settings: Settings, store: AnalyticsStoreProtocol, cache: CacheBackendProtocol | None = None) -> None:
        self._settings = settings
        self._store = store
        self._cache = cache
        self._cache_namespace = "analytics"
        self._cache_ttl = settings.cache_ttl_seconds

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
        self._invalidate_cache()
        return record.to_event()

    def get_user_events(
        self,
        *,
        user_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AnalyticsEvent]:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "user_events", user_id, event_type, limit)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return [AnalyticsEvent.model_validate(item) for item in cached]
        events = [event.to_event() for event in self._store.list_user_events(user_id=user_id, event_type=event_type, limit=limit)]
        self._cache_set(cache_key, [event.model_dump(mode="json") for event in events])
        return events

    def get_user_engagement_metrics(self, *, user_id: str) -> UserEngagementMetrics:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "user_metrics", user_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return UserEngagementMetrics.model_validate(cached)

        metrics = self._store.get_user_engagement_metrics(user_id=user_id)
        result = UserEngagementMetrics(
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
        self._cache_set(cache_key, result.model_dump(mode="json"))
        return result

    def get_platform_overview(self) -> PlatformOverview:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "platform_overview")
        cached = self._cache_get(cache_key)
        if cached is not None:
            return PlatformOverview.model_validate(cached)

        overview = self._store.get_platform_overview()
        result = PlatformOverview(
            total_users=overview["total_users"],
            total_events=overview["total_events"],
            active_users_last_7_days=overview["active_users_last_7_days"],
            active_users_last_30_days=overview["active_users_last_30_days"],
            total_lesson_views=overview["total_lesson_views"],
            total_lesson_completions=overview["total_lesson_completions"],
            total_conversations=overview["total_conversations"],
            total_messages=overview["total_messages"],
        )
        self._cache_set(cache_key, result.model_dump(mode="json"))
        return result

    def get_event_breakdown(self) -> list[EventBreakdown]:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "event_breakdown")
        cached = self._cache_get(cache_key)
        if cached is not None:
            return [EventBreakdown.model_validate(item) for item in cached]

        breakdown = self._store.get_event_breakdown()
        result = [EventBreakdown(
            event_type=item["event_type"],
            count=item["count"],
            percentage=item["percentage"],
        ) for item in breakdown]
        self._cache_set(cache_key, [item.model_dump(mode="json") for item in result])
        return result

    def get_daily_activity(self, days: int = 30) -> list[DailyActivity]:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "daily_activity", days)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return [DailyActivity.model_validate(item) for item in cached]

        activity = self._store.get_daily_activity(days=days)
        result = [DailyActivity(
            date=item["date"],
            event_count=item["event_count"],
            unique_users=item["unique_users"],
        ) for item in activity]
        self._cache_set(cache_key, [item.model_dump(mode="json") for item in result])
        return result

    def get_top_users_by_engagement(self, limit: int = 10) -> list[UserEngagementMetrics]:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "top_users", limit)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return [UserEngagementMetrics.model_validate(item) for item in cached]

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
        self._cache_set(cache_key, [item.model_dump(mode="json") for item in metrics_list])
        return metrics_list


    def _cache_version(self) -> int:
        if self._cache is None:
            return 0
        return self._cache.get_version(self._cache_namespace)

    def _cache_get(self, cache_key: str):
        if self._cache is None:
            return None
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        return json.loads(cached)

    def _cache_set(self, cache_key: str, value: object) -> None:
        if self._cache is None:
            return
        self._cache.set(
            cache_key,
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str),
            ttl_seconds=self._cache_ttl,
        )

    def _invalidate_cache(self) -> None:
        if self._cache is not None:
            self._cache.bump_version(self._cache_namespace)

    def generate_analytics_report(self) -> AnalyticsReport:
        return AnalyticsReport(
            overview=self.get_platform_overview(),
            event_breakdown=self.get_event_breakdown(),
            daily_activity=self.get_daily_activity(days=30),
            top_users_by_engagement=self.get_top_users_by_engagement(limit=10),
        )
