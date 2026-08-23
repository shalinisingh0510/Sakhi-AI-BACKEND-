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
from app.services.wellness_dashboard_service import WellnessDashboardService
from app.schemas.dashboard import WellnessDashboardResponse

router = APIRouter(prefix="/wellness", tags=["wellness"])

def get_wellness_service(db: Session = Depends(get_db)) -> WellnessService:
    return WellnessService(db)

def get_dashboard_service(db: Session = Depends(get_db)) -> WellnessDashboardService:
    return WellnessDashboardService(db)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=WellnessDashboardResponse)
def get_dashboard(
    local_date: date = Query(default_factory=date.today),
    current_user: StoredUser = Depends(get_current_user),
    dashboard_service: WellnessDashboardService = Depends(get_dashboard_service),
) -> Any:
    """Get the aggregated wellness dashboard data."""
    return dashboard_service.get_dashboard(current_user.id, local_date)


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


@router.get("/symptoms/{log_id}", response_model=SymptomLogResponse)
def get_symptom(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.get_symptom(current_user.id, log_id)


@router.patch("/symptoms/{log_id}", response_model=SymptomLogResponse)
def update_symptom(
    log_id: str,
    data: dict[str, Any],
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.update_symptom(current_user.id, log_id, data)


@router.delete("/symptoms/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    wellness_service.delete_symptom(current_user.id, log_id)
    return None

# ---------------------------------------------------------------------------
# Mood & Energy
# ---------------------------------------------------------------------------
from app.schemas.wellness import (
    MoodLogCreate, MoodLogResponse, EnergyLogCreate, EnergyLogResponse
)

@router.get("/mood", response_model=list[MoodLogResponse])
def list_moods(
    limit: int = Query(30, ge=1, le=100),
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.list_moods(current_user.id, limit=limit)

@router.post("/mood", response_model=MoodLogResponse)
def log_mood(
    data: MoodLogCreate,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.log_mood(current_user.id, data)

@router.get("/mood/{log_id}", response_model=MoodLogResponse)
def get_mood(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.get_mood(current_user.id, log_id)

@router.patch("/mood/{log_id}", response_model=MoodLogResponse)
def update_mood(
    log_id: str,
    data: dict[str, Any],
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.update_mood(current_user.id, log_id, data)

@router.delete("/mood/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mood(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    wellness_service.delete_mood(current_user.id, log_id)
    return None

@router.get("/energy", response_model=list[EnergyLogResponse])
def list_energy(
    limit: int = Query(30, ge=1, le=100),
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.list_energy(current_user.id, limit=limit)

@router.post("/energy", response_model=EnergyLogResponse)
def log_energy(
    data: EnergyLogCreate,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.log_energy(current_user.id, data)

@router.get("/energy/{log_id}", response_model=EnergyLogResponse)
def get_energy(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.get_energy(current_user.id, log_id)

@router.patch("/energy/{log_id}", response_model=EnergyLogResponse)
def update_energy(
    log_id: str,
    data: dict[str, Any],
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    return wellness_service.update_energy(current_user.id, log_id, data)

@router.delete("/energy/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_energy(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    wellness_service: WellnessService = Depends(get_wellness_service),
) -> Any:
    wellness_service.delete_energy(current_user.id, log_id)
    return None
