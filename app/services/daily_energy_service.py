"""Service for aggregating daily energy overview (Phase 6/7)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.schemas.energy import CalculationStatus, EnergySummaryResponse
from app.services.activity_service import ActivityService
from app.services.energy_expenditure_service import EnergyExpenditureService
from app.services.nutrition_service import NutritionService


class DailyEnergyService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_service = ActivityService(db)
        self.nutrition_service = NutritionService(db)

    def _get_health_profile(self, user_id: str) -> HealthProfile | None:
        stmt = select(HealthProfile).where(HealthProfile.user_id == user_id)
        return self.db.scalars(stmt).first()

    def get_daily_summary(self, user_id: str, target_date: date) -> EnergySummaryResponse:
        profile = self._get_health_profile(user_id)
        if not profile:
            raise ValueError("Health profile not found")

        # 1. Intake
        nutrition_summary = self.nutrition_service.get_daily_summary(user_id, target_date)
        calories_consumed = nutrition_summary.totals.calories

        # 2. Activity
        activity_summary = self.activity_service.get_activities_for_date(user_id, target_date)
        activity_calories = activity_summary.total_estimated_calories_burned

        # 3. BMR / Baseline TDEE
        baseline_tdee, calc_status = EnergyExpenditureService.calculate_tdee_baseline(profile, target_date)

        # 4. Aggregation & Balance
        if calc_status == CalculationStatus.SUCCESS and baseline_tdee is not None:
            total_expenditure = baseline_tdee + activity_calories
            energy_balance = calories_consumed - total_expenditure
            
            return EnergySummaryResponse(
                target_date=target_date,
                calories_consumed=calories_consumed,
                estimated_bmr=baseline_tdee,
                activity_calories_burned=activity_calories,
                total_estimated_expenditure=round(total_expenditure, 2),
                energy_balance=round(energy_balance, 2),
                calculation_status=CalculationStatus.SUCCESS,
                activity_summary=activity_summary,
            )
        else:
            # Teen gating or insufficient data
            return EnergySummaryResponse(
                target_date=target_date,
                calories_consumed=calories_consumed,
                estimated_bmr=None,
                activity_calories_burned=activity_calories,
                total_estimated_expenditure=None,
                energy_balance=None,
                calculation_status=calc_status,
                activity_summary=activity_summary,
            )
