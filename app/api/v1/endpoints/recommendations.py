from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_recommendation_service
from app.schemas.recommendation import RecommendedLesson
from app.services.auth import StoredUser
from app.services.lessons import InvalidLessonContentError
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/lessons", response_model=list[RecommendedLesson])
def recommend_lessons(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations to return"),
    include_completed: bool = Query(default=False, description="Include completed lessons for review"),
    content_language: str | None = Query(default=None),
    current_user: StoredUser = Depends(get_current_user),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> list[RecommendedLesson]:
    try:
        return recommendation_service.recommend_lessons(
            user=current_user,
            limit=limit,
            include_completed=include_completed,
            content_language=content_language,
        )
    except InvalidLessonContentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc