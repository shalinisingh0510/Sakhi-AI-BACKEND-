"""Activity Tracking API endpoints (Phase 6/7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate
from app.services.activity_service import ActivityNotFoundError, ActivityService
from app.services.auth import StoredUser

router = APIRouter(tags=["activity"])


def _get_service(db: Session = Depends(get_db)) -> ActivityService:
    return ActivityService(db)


@router.post(
    "/activity",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a new activity",
)
def add_activity(
    body: ActivityCreate,
    current_user: StoredUser = Depends(get_current_user),
    service: ActivityService = Depends(_get_service),
) -> ActivityResponse:
    try:
        return service.add_activity(current_user.id, body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.patch(
    "/activity/{activity_id}",
    response_model=ActivityResponse,
    summary="Update an existing activity log",
)
def update_activity(
    activity_id: str,
    body: ActivityUpdate,
    current_user: StoredUser = Depends(get_current_user),
    service: ActivityService = Depends(_get_service),
) -> ActivityResponse:
    try:
        return service.update_activity(current_user.id, activity_id, body)
    except ActivityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )


@router.delete(
    "/activity/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity log",
)
def delete_activity(
    activity_id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: ActivityService = Depends(_get_service),
) -> None:
    try:
        service.delete_activity(current_user.id, activity_id)
    except ActivityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
