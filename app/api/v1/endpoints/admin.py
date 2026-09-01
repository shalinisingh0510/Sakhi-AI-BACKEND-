from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_analytics_service,
    get_auth_service,
    get_feedback_service,
    get_lesson_service,
    get_notification_service,
    pagination_params,
    require_roles,
)
from app.schemas.auth import PublicUser, UpdateRoleRequest
from app.schemas.monetization import SponsorCreate, SponsorUpdate, SponsorResponse, AffiliatePartnerCreate, AffiliatePartnerUpdate, AffiliatePartnerResponse, AffiliateProductCreate, AffiliateProductUpdate, AffiliateProductResponse
from app.schemas.feedback import FeedbackItem, FeedbackOverview, UpdateFeedbackStatusRequest
from app.schemas.lesson import CreateLessonRequest, LessonDetail, LessonSummary, UpdateLessonRequest
from app.schemas.notification import CreateNotificationRequest, NotificationDispatchResult
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, InvalidRoleError, StoredUser, UserNotFoundError
from app.services.feedback import FeedbackNotFoundError, FeedbackService, InvalidFeedbackError
from app.services.lessons import DuplicateLessonSlugError, InvalidLessonContentError, LessonNotFoundError, LessonService
from app.services.notifications import NotificationService
from app.services.monetization_service import MonetizationService
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db

from app.api.v1.endpoints.learning import get_learning_service
from app.services.learning_service import LearningService, TopicNotFoundError
from app.schemas.learning import (
    TopicCreate, TopicUpdate, SubtopicCreate, SubtopicUpdate, 
    TopicResponse, SubtopicResponse, 
    ResearchSourceCreate, ResearchSourceResponse,
    ArticleGenerationResponse, LocalizationRequest, FactValidationResponse
)
from app.services.research_service import ResearchService
from app.services.content_generation_service import ContentGenerationService
import os

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
    feedback_service: FeedbackService = Depends(get_feedback_service),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> dict:
    """Combined admin dashboard stats â€” single request covers users, content, activity, and feedback."""
    platform = analytics_service.get_platform_overview()
    feedback = feedback_service.get_overview()
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
        "feedback": feedback.model_dump(),
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


@router.get("/feedback", response_model=list[FeedbackItem])
def list_feedback(
    pagination: tuple[int, int] = Depends(pagination_params),
    feedback_status: str | None = Query(default=None, description="Filter by feedback status"),
    category: str | None = Query(default=None, description="Filter by feedback category"),
    _current_user: StoredUser = Depends(require_roles("admin")),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> list[FeedbackItem]:
    offset, limit = pagination
    try:
        return feedback_service.list_feedback(status=feedback_status, category=category, limit=limit, offset=offset)
    except InvalidFeedbackError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/feedback/{feedback_id}/status", response_model=FeedbackItem)
def update_feedback_status(
    feedback_id: str,
    payload: UpdateFeedbackStatusRequest,
    _current_user: StoredUser = Depends(require_roles("admin")),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackItem:
    try:
        return feedback_service.update_feedback_status(
            feedback_id=feedback_id,
            status=payload.status,
            admin_notes=payload.admin_notes,
        )
    except FeedbackNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidFeedbackError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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


# ---------------------------------------------------------------------------
# Taxonomy Admin Endpoints
# ---------------------------------------------------------------------------

@router.post("/learning/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate,
    _current_user: StoredUser = Depends(require_roles("admin")),
    learning_service: LearningService = Depends(get_learning_service),
) -> TopicResponse:
    return learning_service.create_topic(payload)


@router.put("/learning/topics/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: str,
    payload: TopicUpdate,
    _current_user: StoredUser = Depends(require_roles("admin")),
    learning_service: LearningService = Depends(get_learning_service),
) -> TopicResponse:
    try:
        return learning_service.update_topic(topic_id, payload)
    except TopicNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/learning/topics/{topic_id}/subtopics", response_model=SubtopicResponse, status_code=status.HTTP_201_CREATED)
def create_subtopic(
    topic_id: str,
    payload: SubtopicCreate,
    _current_user: StoredUser = Depends(require_roles("admin")),
    learning_service: LearningService = Depends(get_learning_service),
) -> SubtopicResponse:
    try:
        return learning_service.create_subtopic(topic_id, payload)
    except TopicNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/learning/subtopics/{subtopic_id}", response_model=SubtopicResponse)
def update_subtopic(
    subtopic_id: str,
    payload: SubtopicUpdate,
    _current_user: StoredUser = Depends(require_roles("admin")),
    learning_service: LearningService = Depends(get_learning_service),
) -> SubtopicResponse:
    try:
        return learning_service.update_subtopic(subtopic_id, payload)
    except TopicNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Research Ingestion Admin Endpoints (Phase 2)
# ---------------------------------------------------------------------------

def get_research_service(db: AsyncSession = Depends(get_db)) -> ResearchService:
    return ResearchService(db)

@router.post("/research/ingest", response_model=ResearchSourceResponse, status_code=status.HTTP_201_CREATED)
async def ingest_research(
    payload: ResearchSourceCreate,
    _current_user: StoredUser = Depends(require_roles("admin")),
    research_service: ResearchService = Depends(get_research_service),
) -> ResearchSourceResponse:
    return await research_service.ingest_url(payload.url)

@router.get("/research", response_model=list[ResearchSourceResponse])
def list_research(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _current_user: StoredUser = Depends(require_roles("admin")),
    research_service: ResearchService = Depends(get_research_service),
):
    return research_service.list_sources(skip=skip, limit=limit)

@router.get("/research/{source_id}", response_model=ResearchSourceResponse)
def get_research_source(
    source_id: str,
    _current_user: StoredUser = Depends(require_roles("admin")),
    research_service: ResearchService = Depends(get_research_service),
):
    return research_service.get_source(source_id)

# ---------------------------------------------------------------------------
# Content Generation & Localization Admin Endpoints (Phase 3)
# ---------------------------------------------------------------------------

def get_generation_service(db: AsyncSession = Depends(get_db)) -> ContentGenerationService:
    api_key = os.getenv("OPENAI_API_KEY", "")
    return ContentGenerationService(db=db, api_key=api_key)

@router.post("/research/{source_id}/generate", response_model=ArticleGenerationResponse, status_code=status.HTTP_201_CREATED)
def generate_english_article(
    source_id: str,
    current_user: StoredUser = Depends(require_roles("admin")),
    gen_service: ContentGenerationService = Depends(get_generation_service),
):
    return gen_service.generate_english_article(source_id, author_id=current_user.id)

@router.post("/learning/{content_id}/localize", response_model=ArticleGenerationResponse)
def localize_article(
    content_id: str,
    payload: LocalizationRequest,
    current_user: StoredUser = Depends(require_roles("admin")),
    gen_service: ContentGenerationService = Depends(get_generation_service),
):
    return gen_service.localize_article(content_id, payload.target_language, author_id=current_user.id)

@router.post("/learning/{content_id}/validate", response_model=FactValidationResponse)
def validate_article(
    content_id: str,
    _current_user: StoredUser = Depends(require_roles("admin")),
    gen_service: ContentGenerationService = Depends(get_generation_service),
):
    return gen_service.validate_content(content_id)
