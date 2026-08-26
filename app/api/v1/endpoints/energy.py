"""Energy Overview API endpoints (Phase 6/7)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.energy import EnergySummaryResponse
from app.services.auth import StoredUser
from app.services.daily_energy_service import DailyEnergyService

router = APIRouter(tags=["energy"])


def _get_service(db: Session = Depends(get_db)) -> DailyEnergyService:
    return DailyEnergyService(db)


@router.get(
    "/energy/today",
    response_model=EnergySummaryResponse,
    summary="Get daily energy overview (Consumed vs Expended)",
)
def get_daily_energy_overview(
    target_date: date | None = Query(None, description="ISO date (YYYY-MM-DD). Defaults to today."),
    current_user: StoredUser = Depends(get_current_user),
    service: DailyEnergyService = Depends(_get_service),
) -> EnergySummaryResponse:
    if target_date is None:
        target_date = date.today()

    try:
        return service.get_daily_summary(current_user.id, target_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
