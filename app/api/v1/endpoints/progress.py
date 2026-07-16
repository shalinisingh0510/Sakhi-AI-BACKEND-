from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_progress_service
from app.schemas.progress import LessonProgressItem, ProgressOverview, UpdateProgressRequest
from app.services.auth import StoredUser
from app.services.lessons import LessonNotFoundError
from app.services.progress import InvalidProgressError, ProgressNotFoundError, ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=list[LessonProgressItem])
def list_progress(
    current_user: StoredUser = Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
) -> list[LessonProgressItem]:
    return progress_service.list_progress(user_id=current_user.id)


@router.get("/summary", response_model=ProgressOverview)
def get_progress_summary(
    current_user: StoredUser = Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
) -> ProgressOverview:
    return progress_service.summarize_progress(user_id=current_user.id)


@router.get("/lessons/{lesson_slug}", response_model=LessonProgressItem)
def get_lesson_progress(
    lesson_slug: str,
    current_user: StoredUser = Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
) -> LessonProgressItem:
    try:
        return progress_service.get_progress(user_id=current_user.id, lesson_slug=lesson_slug)
    except ProgressNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LessonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/lessons/{lesson_slug}", response_model=LessonProgressItem)
def update_lesson_progress(
    lesson_slug: str,
    payload: UpdateProgressRequest,
    current_user: StoredUser = Depends(get_current_user),
    progress_service: ProgressService = Depends(get_progress_service),
) -> LessonProgressItem:
    try:
        return progress_service.upsert_progress(
            user_id=current_user.id,
            lesson_slug=lesson_slug,
            status=payload.status,
            progress_percent=payload.progress_percent,
            notes=payload.notes,
        )
    except InvalidProgressError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LessonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
