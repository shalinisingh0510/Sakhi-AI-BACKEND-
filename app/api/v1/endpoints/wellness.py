"""Wellness API endpoints."""

from __future__ import annotations
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.wellness import (
    DailyCheckInCreate,
    DailyCheckInResponse,
    SymptomLogCreate,
    SymptomLogResponse,
)
from app.services.auth import StoredUser
from app.services.wellness_service import WellnessService

router = APIRouter(prefix="/wellness", tags=["wellness"])

def get_wellness_service(db: Session = Depends(get_db)) -> WellnessService:
    return WellnessService(db)


# ---------------------------------------------------------------------------
# Daily Check-in
# ---------------------------------------------------------------------------

@router.get("/check-in/today", response_model=DailyCheckInResponse)
def get_today_checkin(
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    """Get the daily check-in data for today."""
    return wellness_service.get_daily_checkin(current_user.id, date.today())


@router.post("/check-in", response_model=DailyCheckInResponse)
def submit_checkin(
    data: DailyCheckInCreate,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    """Submit the daily check-in (upserts mood/energy, replaces symptoms for that date)."""
    return wellness_service.submit_daily_checkin(current_user.id, data)


# ---------------------------------------------------------------------------
# Symptoms (Standalone CRUD)
# ---------------------------------------------------------------------------

@router.get("/symptoms", response_model=list[SymptomLogResponse])
def list_symptoms(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.list_symptoms(current_user.id, limit=limit, offset=offset)


@router.post("/symptoms", response_model=SymptomLogResponse)
def log_symptom(
    data: SymptomLogCreate,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.log_symptom(current_user.id, data)


@router.delete("/symptoms/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    wellness_service.delete_symptom(current_user.id, log_id)
    return None

# Note: Mood and Energy standalone GET/DELETE can be added here following the same pattern, 
# but the check-in covers the primary use-case as defined in the spec.
