"""Health Context Builder to assemble data for AI personalization."""

from datetime import date, datetime
from typing import Literal, Sequence
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.services.longitudinal.data_service import LongitudinalDataService
from app.services.longitudinal.trend_engine import WellnessTrendEngine
from app.services.longitudinal.date_range import get_date_range

ContextScope = Literal["PROFILE", "CYCLE", "SYMPTOMS", "MOOD", "ENERGY", "NUTRITION", "ACTIVITY", "LONGITUDINAL"]

class AIHealthContext(BaseModel):
    context_schema_version: str = "health-context-v1"
    data_through: str
    scopes_provided: list[ContextScope]
    
    # Optional sections based on scope
    profile: dict | None = None
    energy_trends: dict | None = None
    symptoms_summary: dict | None = None
    activity_trends: dict | None = None

class HealthContextBuilder:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.data_service = LongitudinalDataService(db)

    def _get_profile(self) -> HealthProfile | None:
        # Note: In a real implementation we would fetch this from DB
        from sqlalchemy import select
        stmt = select(HealthProfile).where(HealthProfile.user_id == self.user_id)
        return self.db.scalars(stmt).first()

    def build_context(self, scopes: list[ContextScope]) -> AIHealthContext | None:
        profile = self._get_profile()
        
        # If AI personalization is disabled, return no context
        if not profile or not profile.ai_health_personalization_enabled:
            return None
            
        today = date.today()
        start_30d, end_30d = get_date_range(today, "30d")
        start_60d, end_60d = get_date_range(today, "60d")
        
        context = AIHealthContext(
            data_through=today.isoformat(),
            scopes_provided=scopes
        )
        
        if "PROFILE" in scopes:
            context.profile = {
                "source": "USER_REPORTED",
                "biological_sex": profile.biological_sex,
                "weight_kg": profile.weight_kg,
                "height_cm": profile.height_cm,
                "activity_level": profile.activity_level
            }
            
        if "ENERGY" in scopes or "LONGITUDINAL" in scopes:
            curr_energy = self.data_service.get_energy_history(self.user_id, start_30d, end_30d)
            prev_energy = self.data_service.get_energy_history(self.user_id, start_60d, start_30d)
            trend = WellnessTrendEngine.analyze_energy_trend(curr_energy, prev_energy)
            
            context.energy_trends = {
                "source": "DERIVED_PATTERN",
                "average_30d": trend.current_value,
                "trend_direction": trend.direction.value,
                "confidence": trend.confidence.value
            }
            
        if "SYMPTOMS" in scopes or "LONGITUDINAL" in scopes:
            curr_symptoms = self.data_service.get_symptom_history(self.user_id, start_30d, end_30d)
            context.symptoms_summary = {
                "source": "USER_REPORTED",
                "total_logs_30d": len(curr_symptoms),
            }
            
        if "ACTIVITY" in scopes or "LONGITUDINAL" in scopes:
            curr_act = self.data_service.get_activity_history(self.user_id, start_30d, end_30d)
            prev_act = self.data_service.get_activity_history(self.user_id, start_60d, start_30d)
            trend = WellnessTrendEngine.analyze_activity_trend(curr_act, prev_act)
            
            context.activity_trends = {
                "source": "DERIVED_PATTERN",
                "total_duration_30d": trend.current_value,
                "trend_direction": trend.direction.value,
                "confidence": trend.confidence.value
            }
            
        return context
