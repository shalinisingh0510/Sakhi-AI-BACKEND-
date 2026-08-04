from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user, get_feedback_service, pagination_params
from app.schemas.feedback import FeedbackItem, SubmitFeedbackRequest
from app.services.auth import StoredUser
from app.services.feedback import FeedbackNotFoundError, FeedbackService, InvalidFeedbackError

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackItem, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: SubmitFeedbackRequest,
    current_user: StoredUser = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackItem:
    try:
        return feedback_service.submit_feedback(
            user_id=current_user.id,
            category=payload.category,
            subject=payload.subject,
            message=payload.message,
            rating=payload.rating,
        )
    except InvalidFeedbackError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[FeedbackItem])
def list_my_feedback(
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> list[FeedbackItem]:
    offset, limit = pagination
    return feedback_service.list_feedback(user_id=current_user.id, limit=limit, offset=offset)
