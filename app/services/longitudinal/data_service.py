"""Longitudinal Data Service to retrieve time-bounded datasets."""

from datetime import date
from typing import Sequence, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.models.menstrual_cycle import MenstrualCycle
from app.models.symptom_log import SymptomLog
from app.models.mood_log import MoodLog
from app.models.energy_log import EnergyLog
from app.models.activity import ActivityLog
from app.models.nutrition import NutritionLog

class LongitudinalDataService:
    def __init__(self, db: Session):
        self.db = db

    def _get_profile_id(self, user_id: str) -> str | None:
        stmt = select(HealthProfile.id).where(HealthProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_profile(self, user_id: str) -> Optional[HealthProfile]:
        return self.db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id)).scalar_one_or_none()

    def get_cycle_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[MenstrualCycle]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
        
        # Note: MenstrualCycle uses cycle_start_date instead of log_date
        stmt = select(MenstrualCycle).where(
            MenstrualCycle.health_profile_id == profile_id,
            MenstrualCycle.cycle_start_date >= start_date,
            MenstrualCycle.cycle_start_date <= end_date
        ).order_by(MenstrualCycle.cycle_start_date.asc())
        
        return self.db.scalars(stmt).all()

    def get_symptom_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[SymptomLog]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
            
        stmt = select(SymptomLog).where(
            SymptomLog.health_profile_id == profile_id,
            SymptomLog.log_date >= start_date,
            SymptomLog.log_date <= end_date
        ).order_by(SymptomLog.log_date.asc())
        
        return self.db.execute(stmt).scalars().all()

    def get_mood_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[MoodLog]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
            
        stmt = select(MoodLog).where(
            MoodLog.health_profile_id == profile_id,
            MoodLog.log_date >= start_date,
            MoodLog.log_date <= end_date
        ).order_by(MoodLog.log_date.asc())
        
        return self.db.scalars(stmt).all()

    def get_energy_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[EnergyLog]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
            
        stmt = select(EnergyLog).where(
            EnergyLog.health_profile_id == profile_id,
            EnergyLog.log_date >= start_date,
            EnergyLog.log_date <= end_date
        ).order_by(EnergyLog.log_date.asc())
        
        return self.db.scalars(stmt).all()

    def get_nutrition_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[NutritionLog]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
            
        stmt = select(NutritionLog).where(
            NutritionLog.health_profile_id == profile_id,
            NutritionLog.log_date >= start_date,
            NutritionLog.log_date <= end_date
        ).order_by(NutritionLog.log_date.asc())
        
        return self.db.scalars(stmt).all()

    def get_activity_history(self, user_id: str, start_date: date, end_date: date) -> Sequence[ActivityLog]:
        profile_id = self._get_profile_id(user_id)
        if not profile_id:
            return []
            
        stmt = select(ActivityLog).where(
            ActivityLog.health_profile_id == profile_id,
            ActivityLog.activity_date >= start_date,
            ActivityLog.activity_date <= end_date
        ).order_by(ActivityLog.activity_date.asc())
        
        return self.db.scalars(stmt).all()
