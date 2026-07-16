from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_auth_service, get_lesson_service, require_roles
from app.schemas.auth import PublicUser, UpdateRoleRequest
from app.schemas.lesson import CreateLessonRequest, LessonDetail, LessonSummary, UpdateLessonRequest
from app.services.auth import AuthService, InvalidRoleError, StoredUser, UserNotFoundError
from app.services.lessons import DuplicateLessonSlugError, InvalidLessonContentError, LessonNotFoundError, LessonService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def admin_overview(current_user: StoredUser = Depends(require_roles("admin"))) -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Admin access granted",
        "user": current_user.email,
    }


@router.get("/users", response_model=list[PublicUser])
def list_users(
    _current_user: StoredUser = Depends(require_roles("admin")),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[PublicUser]:
    return [user.to_public_user() for user in auth_service.list_users()]


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
