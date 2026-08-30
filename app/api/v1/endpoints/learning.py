"""Learning Content API endpoints for Sakhi AI — Phase 1+2.

Public routes (authenticated users):
  GET  /api/v1/learning                          — paginated feed (with topic/subtopic/audience filters)
  GET  /api/v1/learning/topics                   — list all active topics with subtopics
  GET  /api/v1/learning/topics/{slug}            — single topic + subtopics
  GET  /api/v1/learning/topics/{slug}/content    — paginated content for a topic
  GET  /api/v1/learning/progress/summary         — user's learning stats
  GET  /api/v1/learning/history                  — user's learning history
  GET  /api/v1/learning/bookmarks                — user's saved learning
  POST /api/v1/learning/{id}/bookmark            — toggle bookmark
  GET  /api/v1/learning/{id}                     — single PUBLISHED content item
  GET  /api/v1/learning/{id}/related             — related content
  GET  /api/v1/learning/{id}/progress            — user's progress on an item
  POST /api/v1/learning/{id}/progress            — update progress

Admin routes (role=admin required):
  GET    /api/v1/admin/learning              — all content (any status)
  POST   /api/v1/admin/learning              — create content
  PATCH  /api/v1/admin/learning/{id}         — update content
  POST   /api/v1/admin/learning/{id}/publish — publish
  POST   /api/v1/admin/learning/{id}/archive — archive
  DELETE /api/v1/admin/learning/{id}         — hard delete
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, pagination_params, require_roles
from app.db.dependencies import get_db
from app.schemas.learning import (
    LearningContentCreate,
    LearningContentListResponse,
    LearningContentResponse,
    LearningContentUpdate,
    LearningProgressResponse,
    LearningProgressUpdate,
    LearningSummaryResponse,
    LearningHistoryResponse,
    TopicResponse,
    TopicsListResponse,
    LearningPathListResponse,
    LearningPathResponse,
    LearningPathProgressResponse,
)
from app.services.auth import StoredUser
from app.services.learning_service import LearningContentNotFoundError, TopicNotFoundError, LearningService
from app.models.health_profile import HealthProfile
from datetime import date
from sqlalchemy import select

router = APIRouter(tags=["learning"])


def get_learning_service(request: Request, db: Session = Depends(get_db)) -> LearningService:
    return LearningService(db, storage_service=request.app.state.storage_service)

def get_learning_context(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    lang_map = {"english": "en", "hindi": "hi", "marathi": "mr"}
    user_lang = lang_map.get((current_user.preferred_language or "").lower(), "en")

    user_audience = "ADULT"
    profile = db.scalar(select(HealthProfile).where(HealthProfile.user_id == current_user.id))
    if profile and profile.date_of_birth:
        today = date.today()
        dob = profile.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            user_audience = "TEEN"
        
    return {"language": user_lang, "audience": user_audience}


# ---------------------------------------------------------------------------
# Topic Endpoints (Phase 1)
# ---------------------------------------------------------------------------


@router.get(
    "/learning/topics",
    response_model=TopicsListResponse,
    summary="List all active topics with subtopics",
)
def get_topics(
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    topics = service.get_topics(active_only=True)
    return {"items": topics, "total": len(topics)}


@router.get(
    "/learning/topics/{slug}",
    response_model=TopicResponse,
    summary="Get a single topic by slug (with subtopics)",
)
def get_topic(
    slug: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.get_topic_by_slug(slug)
    except TopicNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/learning/topics/{slug}/content",
    response_model=LearningContentListResponse,
    summary="Get paginated content for a topic",
)
def get_topic_content(
    slug: str,
    subtopic: Optional[str] = Query(None, description="Subtopic slug filter"),
    content_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    audience: Optional[str] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
    ctx: dict = Depends(get_learning_context),
) -> Any:
    offset, limit = pagination
    try:
        # Enforce language fallback if not explicitly provided
        applied_language = language or ctx["language"]
        
        # Enforce audience: if user is TEEN, they cannot query ADULT
        applied_audience = audience
        if ctx["audience"] == "TEEN":
            applied_audience = "TEEN"  # Force teen (which includes ALL)
        elif not applied_audience:
            applied_audience = "ADULT" # Default to ADULT (which includes ALL)

        items, total = service.get_topic_content(
            topic_slug=slug,
            subtopic_slug=subtopic,
            content_type=content_type,
            language=applied_language,
            audience=applied_audience,
            limit=limit,
            offset=offset,
        )
    except TopicNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {
        "items": items,
        "total": total,
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


# ---------------------------------------------------------------------------
# Public Endpoints (any authenticated user)
# ---------------------------------------------------------------------------


@router.get(
    "/learning",
    response_model=LearningContentListResponse,
    summary="Get paginated public learning feed",
)
def get_learning_feed(
    category: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    # Phase 1 filters
    topic_id: Optional[str] = Query(None),
    subtopic_id: Optional[str] = Query(None),
    audience: Optional[str] = Query(None),
    is_short_form: Optional[bool] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
    ctx: dict = Depends(get_learning_context),
) -> Any:
    offset, limit = pagination
    
    # Language filtering
    applied_language = language or ctx["language"]

    # Audience filtering
    applied_audience = audience
    if ctx["audience"] == "TEEN":
        applied_audience = "TEEN"
    elif not applied_audience:
        applied_audience = "ADULT"

    items, total = service.get_feed(
        category=category,
        content_type=content_type,
        language=applied_language,
        is_featured=is_featured,
        search=search,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        audience=applied_audience,
        is_short_form=is_short_form,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


@router.get(
    "/learning/progress/summary",
    response_model=LearningSummaryResponse,
    summary="Get user learning progress summary",
)
def get_progress_summary(
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    return service.get_user_progress_summary(current_user.id)

# ---------------------------------------------------------------------------
# Learning Paths Endpoints (Phase 5)
# ---------------------------------------------------------------------------

@router.get(
    "/learning/paths",
    response_model=LearningPathListResponse,
    summary="Get paginated list of learning paths",
)
def get_learning_paths(
    topic_slug: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    audience: Optional[str] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
    ctx: dict = Depends(get_learning_context),
) -> Any:
    offset, limit = pagination
    
    applied_language = language or ctx["language"]
    applied_audience = audience
    if ctx["audience"] == "TEEN":
        applied_audience = "TEEN"
    elif not applied_audience:
        applied_audience = "ADULT"

    items, total = service.get_paths(
        topic_slug=topic_slug,
        language=applied_language,
        audience=applied_audience,
        limit=limit,
        offset=offset,
    )
    
    return {
        "items": items,
        "total": total,
        "page": (offset // limit) + 1,
        "page_size": limit,
    }

@router.get(
    "/learning/paths/{slug}",
    response_model=LearningPathResponse,
    summary="Get a single learning path by slug",
)
def get_learning_path(
    slug: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.get_path_by_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get(
    "/learning/paths/{id}/progress",
    response_model=LearningPathProgressResponse,
    summary="Get user progress for a learning path",
)
def get_learning_path_progress(
    id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.get_path_progress(current_user.id, id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))



@router.get(
    "/learning/history",
    response_model=LearningHistoryResponse,
    summary="Get user learning history",
)
def get_learning_history(
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    offset, limit = pagination
    history = service.get_learning_history(current_user.id, limit=limit, offset=offset)
    return {
        "items": history,
        "total": len(history),
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


@router.get(
    "/learning/bookmarks",
    response_model=LearningContentListResponse,
    summary="Get user bookmarked learning content",
)
def get_learning_bookmarks(
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    offset, limit = pagination
    items = service.get_bookmarks(current_user.id, limit=limit, offset=offset)
    return {
        "items": items,
        "total": len(items),
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


@router.post(
    "/learning/{content_id}/bookmark",
    summary="Toggle bookmark for a learning content item",
)
def toggle_bookmark(
    content_id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        service.get_content(content_id)
        saved = service.toggle_bookmark(current_user.id, content_id)
        return {"saved": saved}
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/learning/{id}",
    response_model=LearningContentResponse,
    summary="Get a single PUBLISHED learning content item",
)
def get_learning_item(
    id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
    ctx: dict = Depends(get_learning_context),
) -> Any:
    try:
        content = service.get_content(id)
        
        # Enforce audience access control
        if ctx["audience"] == "TEEN" and content.audience == "ADULT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not eligible to view this content."
            )
            
        return content
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/learning/{content_id}/related",
    response_model=LearningContentListResponse,
    summary="Get related learning content",
)
def get_related_learning_content(
    content_id: str,
    limit: int = Query(4, ge=1, le=10),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        items = service.get_related_content(content_id, limit=limit)
        return {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": limit,
        }
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/learning/{content_id}/progress",
    response_model=LearningProgressResponse,
    summary="Get user progress for a content item",
)
def get_learning_progress(
    content_id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    progress = service.get_progress(current_user.id, content_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Progress record not found."
        )
    return progress


@router.post(
    "/learning/{content_id}/progress",
    response_model=LearningProgressResponse,
    summary="Create or update user progress for a content item",
)
def update_learning_progress(
    content_id: str,
    body: LearningProgressUpdate,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        service.get_content(content_id, admin=False)
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return service.update_progress(
        user_id=current_user.id,
        content_id=content_id,
        completed=body.completed,
        watch_time_seconds=body.watch_time_seconds,
        progress_percent=body.progress_percent,
    )


# ---------------------------------------------------------------------------
# Admin Endpoints (role=admin required)
# ---------------------------------------------------------------------------


@router.get(
    "/admin/learning",
    response_model=LearningContentListResponse,
    summary="[Admin] List all learning content (any status)",
)
def admin_list_content(
    status_filter: Optional[str] = Query(None, alias="status"),
    content_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    topic_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    offset, limit = pagination
    items, total = service.get_admin_list(
        status=status_filter,
        content_type=content_type,
        category=category,
        topic_id=topic_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "page": (offset // limit) + 1,
        "page_size": limit,
    }


@router.get(
    "/admin/learning/{content_id}",
    response_model=LearningContentResponse,
    summary="[Admin] Get a single content item (any status)",
)
def admin_get_content(
    content_id: str,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.get_content(content_id, admin=True)
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/admin/learning",
    response_model=LearningContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create learning content",
)
def create_learning_content(
    body: LearningContentCreate,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.create_content(current_user.id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.patch(
    "/admin/learning/{content_id}",
    response_model=LearningContentResponse,
    summary="[Admin] Update learning content",
)
def update_learning_content(
    content_id: str,
    body: LearningContentUpdate,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.update_content(content_id, body.model_dump(exclude_unset=True))
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post(
    "/admin/learning/{content_id}/publish",
    response_model=LearningContentResponse,
    summary="[Admin] Publish a learning content item",
)
def publish_learning_content(
    content_id: str,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.publish_content(content_id)
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/admin/learning/{content_id}/archive",
    response_model=LearningContentResponse,
    summary="[Admin] Archive a learning content item",
)
def archive_learning_content(
    content_id: str,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.archive_content(content_id)
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/admin/learning/{content_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Delete learning content (hard delete)",
)
def delete_learning_content(
    content_id: str,
    current_user: StoredUser = Depends(require_roles("admin")),
    service: LearningService = Depends(get_learning_service),
) -> None:
    try:
        service.delete_content(content_id)
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
