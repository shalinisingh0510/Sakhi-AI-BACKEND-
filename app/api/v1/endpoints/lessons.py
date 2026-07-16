from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_lesson_service
from app.schemas.lesson import LessonDetail, LessonSummary
from app.services.lessons import LessonNotFoundError, LessonService

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("", response_model=list[LessonSummary])
def list_lessons(
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    search: str | None = Query(default=None),
    lesson_service: LessonService = Depends(get_lesson_service),
) -> list[LessonSummary]:
    return lesson_service.list_lessons(category=category, language=language, search=search)


@router.get("/categories")
def list_categories(lesson_service: LessonService = Depends(get_lesson_service)) -> list[dict[str, int | str]]:
    return lesson_service.list_categories()


@router.get("/{slug}", response_model=LessonDetail)
def get_lesson(
    slug: str,
    lesson_service: LessonService = Depends(get_lesson_service),
) -> LessonDetail:
    try:
        return lesson_service.get_lesson(slug=slug)
    except LessonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
