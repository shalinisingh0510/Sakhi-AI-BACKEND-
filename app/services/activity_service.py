"""Service for Activity Tracking (Phase 6/7)."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityIntensity, ActivityLog, ActivitySource
from app.models.health_profile import HealthProfile
from app.schemas.activity import (
    ActivityCreate,
    ActivityDailySummary,
    ActivityResponse,
    ActivityUpdate,
)


class ActivityNotFoundError(Exception):
    pass


# A simple MET (Metabolic Equivalent of Task) taxonomy
# In a real app, this might be a database table, but a dictionary is fine for Phase 6.
ACTIVITY_MET_MAP: dict[str, dict[str, float]] = {
    "WALKING": {
        ActivityIntensity.LOW: 2.5,
        ActivityIntensity.MODERATE: 3.5,
        ActivityIntensity.HIGH: 4.5,
    },
    "RUNNING": {
        ActivityIntensity.LOW: 6.0,
        ActivityIntensity.MODERATE: 8.0,
        ActivityIntensity.HIGH: 10.0,
    },
    "CYCLING": {
        ActivityIntensity.LOW: 4.0,
        ActivityIntensity.MODERATE: 6.0,
        ActivityIntensity.HIGH: 8.5,
    },
    "SWIMMING": {
        ActivityIntensity.LOW: 4.5,
        ActivityIntensity.MODERATE: 6.0,
        ActivityIntensity.HIGH: 8.0,
    },
    "YOGA": {
        ActivityIntensity.LOW: 2.0,
        ActivityIntensity.MODERATE: 2.5,
        ActivityIntensity.HIGH: 3.0,
    },
    "STRENGTH_TRAINING": {
        ActivityIntensity.LOW: 3.0,
        ActivityIntensity.MODERATE: 5.0,
        ActivityIntensity.HIGH: 6.0,
    },
    "DANCE": {
        ActivityIntensity.LOW: 3.0,
        ActivityIntensity.MODERATE: 4.5,
        ActivityIntensity.HIGH: 6.0,
    },
    "SPORT": {
        ActivityIntensity.LOW: 4.0,
        ActivityIntensity.MODERATE: 6.0,
        ActivityIntensity.HIGH: 8.0,
    },
    "HIKING": {
        ActivityIntensity.LOW: 4.0,
        ActivityIntensity.MODERATE: 5.3,
        ActivityIntensity.HIGH: 6.5,
    },
    "HOUSEHOLD_ACTIVITY": {
        ActivityIntensity.LOW: 2.0,
        ActivityIntensity.MODERATE: 3.0,
        ActivityIntensity.HIGH: 4.0,
    },
    "OTHER": {
        ActivityIntensity.LOW: 2.0,
        ActivityIntensity.MODERATE: 4.0,
        ActivityIntensity.HIGH: 6.0,
    },
}

DEFAULT_MET = 4.0


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_estimated_calories(
        self, activity_type: str, intensity: str, duration_minutes: int, weight_kg: float | None
    ) -> tuple[float, str]:
        """Calculate estimated calories burned using MET formula.
        
        Formula: Calories = (MET * Weight(kg) * 3.5) / 200 * Duration(minutes)
        
        Returns: (calories, calculation_method)
        """
        if weight_kg is None or weight_kg <= 0:
            return 0.0, "insufficient_data"

        activity_key = activity_type.upper()
        if activity_key not in ACTIVITY_MET_MAP:
            activity_key = "OTHER"

        intensity_map = ACTIVITY_MET_MAP[activity_key]
        met = intensity_map.get(intensity.upper(), DEFAULT_MET)
        
        calories = (met * weight_kg * 3.5) / 200.0 * duration_minutes
        
        return round(calories, 2), "met-v1"

    def _get_health_profile(self, user_id: str) -> HealthProfile | None:
        stmt = select(HealthProfile).where(HealthProfile.user_id == user_id)
        return self.db.scalars(stmt).first()

    def get_activities_for_date(self, user_id: str, target_date: date) -> ActivityDailySummary:
        profile = self._get_health_profile(user_id)
        if not profile:
            return ActivityDailySummary(
                activity_date=target_date,
                total_duration_minutes=0,
                total_estimated_calories_burned=0.0,
                total_steps=0,
                activities=[]
            )

        stmt = (
            select(ActivityLog)
            .where(
                ActivityLog.health_profile_id == profile.id,
                ActivityLog.activity_date == target_date,
            )
            .order_by(ActivityLog.created_at.desc())
        )
        activities = self.db.scalars(stmt).all()
        
        return self._aggregate_daily_summary(target_date, activities)
        
    def _aggregate_daily_summary(self, target_date: date, activities: Sequence[ActivityLog]) -> ActivityDailySummary:
        total_duration = sum(a.duration_minutes for a in activities)
        total_calories = sum(a.estimated_calories_burned for a in activities)
        
        total_steps = 0
        has_steps = False
        for a in activities:
            if a.steps is not None:
                total_steps += a.steps
                has_steps = True
                
        return ActivityDailySummary(
            activity_date=target_date,
            total_duration_minutes=total_duration,
            total_estimated_calories_burned=round(total_calories, 2),
            total_steps=total_steps if has_steps else None,
            activities=[ActivityResponse.model_validate(a) for a in activities],
        )

    def add_activity(self, user_id: str, data: ActivityCreate) -> ActivityResponse:
        profile = self._get_health_profile(user_id)
        if not profile:
            raise ValueError("Health profile not found")

        calories, calc_method = self.calculate_estimated_calories(
            activity_type=data.activity_type,
            intensity=data.intensity,
            duration_minutes=data.duration_minutes,
            weight_kg=profile.weight_kg,
        )

        import uuid
        activity = ActivityLog(
            id=str(uuid.uuid4()),
            health_profile_id=profile.id,
            cycle_id=data.cycle_id,
            activity_date=data.activity_date,
            activity_type=data.activity_type.upper(),
            duration_minutes=data.duration_minutes,
            intensity=data.intensity.upper(),
            distance_km=data.distance_km,
            steps=data.steps,
            estimated_calories_burned=calories,
            source=ActivitySource.ESTIMATED,
            calculation_method=calc_method,
            algorithm_version="1.0",
            notes=data.notes,
        )
        
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        
        return ActivityResponse.model_validate(activity)

    def update_activity(self, user_id: str, activity_id: str, data: ActivityUpdate) -> ActivityResponse:
        profile = self._get_health_profile(user_id)
        if not profile:
            raise ValueError("Health profile not found")

        stmt = select(ActivityLog).where(
            ActivityLog.id == activity_id,
            ActivityLog.health_profile_id == profile.id
        )
        activity = self.db.scalars(stmt).first()
        if not activity:
            raise ActivityNotFoundError("Activity not found or does not belong to you")
            
        updated = False
        if data.activity_type is not None:
            activity.activity_type = data.activity_type.upper()
            updated = True
        if data.duration_minutes is not None:
            activity.duration_minutes = data.duration_minutes
            updated = True
        if data.intensity is not None:
            activity.intensity = data.intensity.upper()
            updated = True
            
        if updated:
            # Recalculate calories
            calories, calc_method = self.calculate_estimated_calories(
                activity_type=activity.activity_type,
                intensity=activity.intensity,
                duration_minutes=activity.duration_minutes,
                weight_kg=profile.weight_kg,
            )
            activity.estimated_calories_burned = calories
            activity.calculation_method = calc_method
            
        if data.distance_km is not None:
            activity.distance_km = data.distance_km
        if data.steps is not None:
            activity.steps = data.steps
        if data.notes is not None:
            activity.notes = data.notes
            
        self.db.commit()
        self.db.refresh(activity)
        
        return ActivityResponse.model_validate(activity)

    def delete_activity(self, user_id: str, activity_id: str) -> None:
        profile = self._get_health_profile(user_id)
        if not profile:
            raise ValueError("Health profile not found")
            
        stmt = select(ActivityLog).where(
            ActivityLog.id == activity_id,
            ActivityLog.health_profile_id == profile.id
        )
        activity = self.db.scalars(stmt).first()
        if not activity:
            raise ActivityNotFoundError("Activity not found")
            
        self.db.delete(activity)
        self.db.commit()
