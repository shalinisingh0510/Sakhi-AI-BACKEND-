from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.health_profile import HealthProfile
from app.models.activity import ActivityLog
from app.models.nutrition import NutritionLog
from app.models.symptom_log import SymptomLog
from app.models.energy_log import EnergyLog
from app.models.mood_log import MoodLog
from app.models.cycle_log import MenstrualCycle
from app.models.wellness_plan import WellnessPlan
from app.models.integrations import HealthProviderConnection

class DataExportService:
    """
    Service to handle GDPR/CCPA compliant data exports for a user.
    Aggregates all related health data into a single JSON structure.
    """
    def __init__(self, db: Session):
        self.db = db

    def generate_export(self, user_id: str) -> Dict[str, Any]:
        export_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "user_id": user_id
            },
            "profile": {},
            "activity_logs": [],
            "nutrition_logs": [],
            "symptom_logs": [],
            "energy_logs": [],
            "mood_logs": [],
            "cycles": [],
            "wellness_plans": [],
            "integrations": []
        }

        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        if not profile:
            return export_data

        export_data["profile"] = {
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "dietary_preferences": profile.dietary_preferences,
            "allergies": profile.allergies
        }
        
        # Helper to dump sqlalchemy objects
        def dump_all(model, profile_id):
            records = self.db.query(model).filter(model.health_profile_id == profile_id).all()
            # Simple dictionary conversion, avoiding internal state
            return [{k: v for k, v in r.__dict__.items() if not k.startswith('_')} for r in records]
            
        export_data["activity_logs"] = dump_all(ActivityLog, profile.id)
        export_data["nutrition_logs"] = dump_all(NutritionLog, profile.id)
        export_data["symptom_logs"] = dump_all(SymptomLog, profile.id)
        export_data["energy_logs"] = dump_all(EnergyLog, profile.id)
        export_data["mood_logs"] = dump_all(MoodLog, profile.id)
        export_data["cycles"] = dump_all(MenstrualCycle, profile.id)

        # Plans and Integrations use user_id directly
        plans = self.db.query(WellnessPlan).filter(WellnessPlan.user_id == user_id).all()
        export_data["wellness_plans"] = [{k: v for k, v in r.__dict__.items() if not k.startswith('_')} for r in plans]
        
        connections = self.db.query(HealthProviderConnection).filter(HealthProviderConnection.user_id == user_id).all()
        export_data["integrations"] = [{"provider": r.provider.value, "status": r.status.value} for r in connections]

        # In production, dates and enums must be serialized safely before JSON encoding,
        # which FastAPI/Pydantic would handle if we returned a structured model.
        return export_data
