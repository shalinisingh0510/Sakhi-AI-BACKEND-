from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_analytics_service,
    get_auth_service,
    get_lesson_service,
    get_notification_service,
    require_roles,
)
from app.schemas.auth import PublicUser, UpdateRoleRequest
from app.schemas.lesson import CreateLessonRequest, LessonDetail, LessonSummary, UpdateLessonRequest
from app.schemas.notification import CreateNotificationRequest, NotificationDispatchResult
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, InvalidRoleError, StoredUser, UserNotFoundError
from app.services.lessons import DuplicateLessonSlugError, InvalidLessonContentError, LessonNotFoundError, LessonService
from app.services.notifications import NotificationService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(current_user: StoredUser = Depends(require_roles("admin"))) -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Admin access granted",
        "user": current_user.email,
    }


@router.get("/stats")
def admin_stats(
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> dict:
    """Combined admin dashboard stats — single request covers users, content, and activity."""
    platform = analytics_service.get_platform_overview()
    lessons = lesson_service.list_lessons(published_only=False)
    published_count = sum(1 for l in lessons if l.published)
    unpublished_count = len(lessons) - published_count
    categories = lesson_service.list_categories(published_only=False)

    return {
        "users": {
            "total": platform.total_users,
            "active_last_7_days": platform.active_users_last_7_days,
            "active_last_30_days": platform.active_users_last_30_days,
        },
        "lessons": {
            "total": len(lessons),
            "published": published_count,
            "unpublished": unpublished_count,
            "categories": len(categories),
        },
        "engagement": {
            "total_events": platform.total_events,
            "total_lesson_views": platform.total_lesson_views,
            "total_lesson_completions": platform.total_lesson_completions,
            "total_conversations": platform.total_conversations,
            "total_messages": platform.total_messages,
        },
    }


@router.get("/users", response_model=list[PublicUser])
def list_users(
    search: str | None = Query(default=None, description="Filter by name or email (case-insensitive)"),
    role: str | None = Query(default=None, description="Filter by role: user, admin, moderator"),
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[PublicUser]:
    if search or role:
        users = auth_service.search_users(query=search, role=role)
    else:
        users = auth_service.list_users()
    return [user.to_public_user() for user in users]


@router.patch("/users/{user_id}/role", response_model=PublicUser)
def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
) -> PublicUser:
    try:
        user = auth_service.update_user_role(user_id=user_id, role=payload.role)
    except InvalidRoleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return user.to_public_user()


@router.post("/notifications", response_model=NotificationDispatchResult, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: CreateNotificationRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationDispatchResult:
    users = auth_service.list_users()
    if payload.recipient_user_id is not None:
        users = [user for user in users if user.id == payload.recipient_user_id]
        if not users:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    notifications = notification_service.create_notifications_for_users(
        user_ids=[user.id for user in users],
        title=payload.title,
        body=payload.body,
        notification_type=payload.notification_type,
        metadata=payload.metadata,
    )
    return NotificationDispatchResult(created_count=len(notifications), notifications=notifications)


@router.get("/lessons", response_model=list[LessonSummary])
def list_lessons(
    content_language: str | None = Query(default=None),
    _current_user: StoredUser = Depends(require_roles("admin")),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> list[LessonSummary]:
    try:
        return lesson_service.list_lessons(published_only=False, content_language=content_language)
    except InvalidLessonContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(
    lesson_id: str,
    content_language: str | None = Query(default=None),
    _current_user: StoredUser = Depends(require_roles("admin")),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> LessonDetail:
    try:
        return lesson_service.get_lesson_by_id(lesson_id, content_language=content_language)
    except InvalidLessonContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LessonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/lessons", response_model=LessonDetail, status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: CreateLessonRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> LessonDetail:
    try:
        lesson = lesson_service.create_lesson(
            title=payload.title,
            slug=payload.slug,
            category=payload.category,
            summary=payload.summary,
            language=payload.language,
            audience=payload.audience,
            tags=payload.tags,
            translations=payload.translations,
            sections=payload.sections,
            published=payload.published,
            created_by_user_id=_current_user.id,
        )
    except DuplicateLessonSlugError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidLessonContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return lesson.to_detail()


@router.patch("/lessons/{lesson_id}", response_model=LessonDetail)
def update_lesson(
    lesson_id: str,
    payload: UpdateLessonRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> LessonDetail:
    try:
        lesson = lesson_service.update_lesson(
            lesson_id=lesson_id,
            title=payload.title,
            slug=payload.slug,
            category=payload.category,
            summary=payload.summary,
            language=payload.language,
            audience=payload.audience,
            tags=payload.tags,
            translations=payload.translations,
            sections=payload.sections,
            published=payload.published,
        )
    except DuplicateLessonSlugError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidLessonContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return lesson.to_detail()


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: str,
    _current_user: StoredUser = Depends(require_roles("admin")),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> None:
    try:
        lesson_service.delete_lesson(lesson_id=lesson_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
