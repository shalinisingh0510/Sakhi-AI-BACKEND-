from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_analytics_service, get_current_user, require_roles
from app.schemas.analytics import (
    AnalyticsEvent,
    AnalyticsReport,
    CreateEventRequest,
    DailyActivity,
    EventBreakdown,
    PlatformOverview,
    UserEngagementMetrics,
)
from app.services.analytics import AnalyticsService
from app.services.auth import StoredUser

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", response_model=AnalyticsEvent, status_code=status.HTTP_201_CREATED)
def track_event(
    payload: CreateEventRequest,
    current_user: StoredUser = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsEvent:
    return analytics_service.track_event(
        user_id=current_user.id,
        event_type=payload.event_type,
        metadata=payload.metadata,
    )


@router.get("/events", response_model=list[AnalyticsEvent])
def list_user_events(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: StoredUser = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> list[AnalyticsEvent]:
    return analytics_service.get_user_events(
        user_id=current_user.id,
        event_type=event_type,
        limit=limit,
    )


@router.get("/engagement", response_model=UserEngagementMetrics)
def get_user_engagement(
    current_user: StoredUser = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UserEngagementMetrics:
    return analytics_service.get_user_engagement_metrics(user_id=current_user.id)


@router.get("/platform/overview", response_model=PlatformOverview)
def get_platform_overview(
    _current_user: StoredUser = Depends(require_roles("admin")),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> PlatformOverview:
    return analytics_service.get_platform_overview()


@router.get("/platform/event-breakdown", response_model=list[EventBreakdown])
def get_event_breakdown(
    _current_user: StoredUser = Depends(require_roles("admin")),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> list[EventBreakdown]:
    return analytics_service.get_event_breakdown()


@router.get("/platform/daily-activity", response_model=list[DailyActivity])
def get_daily_activity(
    days: int = Query(default=30, ge=1, le=365),
    _current_user: StoredUser = Depends(require_roles("admin")),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> list[DailyActivity]:
    return analytics_service.get_daily_activity(days=days)


@router.get("/platform/top-users", response_model=list[UserEngagementMetrics])
def get_top_users(
    limit: int = Query(default=10, ge=1, le=50),
    _current_user: StoredUser = Depends(require_roles("admin")),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> list[UserEngagementMetrics]:
    return analytics_service.get_top_users_by_engagement(limit=limit)


@router.get("/platform/report", response_model=AnalyticsReport)
def get_analytics_report(
    _current_user: StoredUser = Depends(require_roles("admin")),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsReport:
    return analytics_service.generate_analytics_report()
