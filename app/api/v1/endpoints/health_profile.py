"""Health Profile API endpoints.

All endpoints require Bearer authentication.
User ID is ALWAYS derived from the auth token — never from request body.

Endpoints:
  GET    /api/v1/health-profile               — get my profile
  POST   /api/v1/health-profile               — create profile
  PATCH  /api/v1/health-profile               — update profile
  GET    /api/v1/health-profile/permissions   — get permission flags
  PATCH  /api/v1/health-profile/permissions   — update permission flags
  GET    /api/v1/health-profile/conditions    — list conditions
  POST   /api/v1/health-profile/conditions    — add condition
  DELETE /api/v1/health-profile/conditions/{id} — remove condition
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.health_profile import (
    HealthConditionCreate,
    HealthConditionResponse,
    HealthPermissionsResponse,
    HealthPermissionsUpdate,
    HealthProfileCreate,
    HealthProfileResponse,
    HealthProfileUpdate,
)
from app.services.auth import StoredUser
from app.services.health_profile import (
    AgeEligibilityError,
    ConditionNotFoundError,
    HealthProfileService,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
)

from sqlalchemy.orm import Session

router = APIRouter(tags=["health-profile"])


def _get_service(db: Session = Depends(get_db)) -> HealthProfileService:
    return HealthProfileService(db)


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health-profile",
    response_model=HealthProfileResponse,
    summary="Get my health profile",
)
def get_health_profile(
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthProfileResponse:
    try:
        return service.get_profile(authenticated_user_id=current_user.id)
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found. Create one first.",
        )


@router.post(
    "/health-profile",
    response_model=HealthProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create my health profile",
)
def create_health_profile(
    body: HealthProfileCreate,
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthProfileResponse:
    try:
        return service.create_profile(
            authenticated_user_id=current_user.id, data=body
        )
    except AgeEligibilityError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        )
    except ProfileAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )


@router.patch(
    "/health-profile",
    response_model=HealthProfileResponse,
    summary="Update my health profile",
)
def update_health_profile(
    body: HealthProfileUpdate,
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthProfileResponse:
    try:
        return service.update_profile(
            authenticated_user_id=current_user.id, data=body
        )
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found. Create one first.",
        )


# ---------------------------------------------------------------------------
# Permissions endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health-profile/permissions",
    response_model=HealthPermissionsResponse,
    summary="Get health tracking permissions",
)
def get_health_permissions(
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthPermissionsResponse:
    try:
        profile = service.get_profile(authenticated_user_id=current_user.id)
        return HealthPermissionsResponse(
            cycle_tracking_enabled=profile.cycle_tracking_enabled,
            nutrition_tracking_enabled=profile.nutrition_tracking_enabled,
            activity_tracking_enabled=profile.activity_tracking_enabled,
            ai_health_personalization_enabled=profile.ai_health_personalization_enabled,
        )
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found. Create one first.",
        )


@router.patch(
    "/health-profile/permissions",
    response_model=HealthPermissionsResponse,
    summary="Update health tracking permissions",
)
def update_health_permissions(
    body: HealthPermissionsUpdate,
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthPermissionsResponse:
    try:
        profile = service.update_permissions(
            authenticated_user_id=current_user.id, data=body
        )
        return HealthPermissionsResponse(
            cycle_tracking_enabled=profile.cycle_tracking_enabled,
            nutrition_tracking_enabled=profile.nutrition_tracking_enabled,
            activity_tracking_enabled=profile.activity_tracking_enabled,
            ai_health_personalization_enabled=profile.ai_health_personalization_enabled,
        )
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health profile not found.",
        )


# ---------------------------------------------------------------------------
# Conditions endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health-profile/conditions",
    response_model=list[HealthConditionResponse],
    summary="List my self-reported health conditions",
)
def get_health_conditions(
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> list[HealthConditionResponse]:
    return service.get_conditions(authenticated_user_id=current_user.id)


@router.post(
    "/health-profile/conditions",
    response_model=HealthConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a self-reported health condition",
)
def add_health_condition(
    body: HealthConditionCreate,
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> HealthConditionResponse:
    return service.add_condition(
        authenticated_user_id=current_user.id, data=body
    )


@router.delete(
    "/health-profile/conditions/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a self-reported health condition",
)
def remove_health_condition(
    condition_id: str,
    current_user: StoredUser = Depends(get_current_user),
    service: HealthProfileService = Depends(_get_service),
) -> None:
    try:
        service.remove_condition(
            authenticated_user_id=current_user.id,
            condition_id=condition_id,
        )
    except ConditionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Condition not found.",
        )
