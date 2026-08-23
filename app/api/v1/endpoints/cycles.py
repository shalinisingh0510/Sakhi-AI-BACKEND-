"""Cycle tracking API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.cycle import (
    CalendarResponse,
    CurrentCycleResponse,
    CycleStatisticsResponse,
    MenstrualCycleResponse,
    PeriodLogCreate,
    PeriodLogResponse,
    PeriodLogUpdate,
)
from app.services.auth import StoredUser
from app.services.cycle_service import CycleService

router = APIRouter(prefix="/cycles", tags=["cycles"])


def get_cycle_service(db: Session = Depends(get_db)) -> CycleService:
    return CycleService(db)


# ---------------------------------------------------------------------------
# Period Logs (Raw data)
# ---------------------------------------------------------------------------


@router.post("/periods", response_model=PeriodLogResponse, status_code=status.HTTP_201_CREATED)
def log_period(
    data: PeriodLogCreate,
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Log a new period. Start date is required."""
    return cycle_service.log_period(current_user.id, data)


@router.get("/periods", response_model=list[PeriodLogResponse])
def list_periods(
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """List recent period logs."""
    return cycle_service.list_periods(current_user.id)


@router.get("/periods/{log_id}", response_model=PeriodLogResponse)
def get_period(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    return cycle_service.get_period(current_user.id, log_id)


@router.patch("/periods/{log_id}", response_model=PeriodLogResponse)
def update_period(
    log_id: str,
    data: PeriodLogUpdate,
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Update a period log (e.g. adding the end_date)."""
    return cycle_service.update_period(current_user.id, log_id, data)


@router.delete("/periods/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    log_id: str,
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Delete a period log."""
    cycle_service.delete_period(current_user.id, log_id)
    return None


# ---------------------------------------------------------------------------
# Cycle Aggregates (Derived data)
# ---------------------------------------------------------------------------


@router.get("/current", response_model=CurrentCycleResponse)
def get_current_cycle(
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Get the current cycle dashboard summary (with estimates)."""
    return cycle_service.get_current_cycle(current_user.id)


@router.get("", response_model=list[MenstrualCycleResponse])
def list_cycles(
    limit: int = Query(12, ge=1, le=50),
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """List historical derived cycles."""
    return cycle_service.list_cycles(current_user.id, limit)


@router.get("/statistics", response_model=CycleStatisticsResponse)
def get_statistics(
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Get cycle statistics and averages."""
    return cycle_service.get_statistics(current_user.id)


@router.get("/calendar", response_model=CalendarResponse)
def get_calendar(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    current_user: StoredUser = Depends(get_current_user),
    cycle_service: CycleService = Depends(get_cycle_service),
) -> Any:
    """Get calendar UI data."""
    return cycle_service.get_calendar(current_user.id, year, month)
