"""Learning Content API endpoints for Sakhi AI.

Public routes (authenticated users):
  GET  /api/v1/learning                      — paginated feed of PUBLISHED content
  GET  /api/v1/learning/progress/summary     — user's learning stats
  GET  /api/v1/learning/{id}                 — single PUBLISHED content item
  GET  /api/v1/learning/{id}/progress        — user's progress on an item
  POST /api/v1/learning/{id}/progress        — update progress

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

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
)
from app.services.auth import StoredUser
from app.services.learning_service import LearningContentNotFoundError, LearningService

router = APIRouter(tags=["learning"])


from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

def get_learning_service(request: Request, db: Session = Depends(get_db)) -> LearningService:
    return LearningService(db, storage_service=request.app.state.storage_service)


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
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    offset, limit = pagination
    items, total = service.get_feed(
        category=category,
        content_type=content_type,
        language=language,
        is_featured=is_featured,
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
    "/learning/progress/summary",
    response_model=LearningSummaryResponse,
    summary="Get user learning progress summary",
)
def get_progress_summary(
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    return service.get_user_progress_summary(current_user.id)


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
        "total": len(history), # Simplification, ideal is total count query
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
        "total": len(items), # Simplification
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
        # Verify content exists
        service.get_content(content_id)
        saved = service.toggle_bookmark(current_user.id, content_id)
        return {"saved": saved}
    except LearningContentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/learning/{content_id}",
    response_model=LearningContentResponse,
    summary="Get a single published learning content item",
)
def get_learning_content(
    content_id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> Any:
    try:
        return service.get_content(content_id, admin=False)
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
