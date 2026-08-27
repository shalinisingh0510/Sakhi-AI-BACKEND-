import uuid
from typing import List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.activity import ActivityLog, ActivitySource
from app.models.health_profile import HealthProfile
from app.services.integrations.provider import ExternalActivityRecord

class IntegrationNormalizer:
    def __init__(self, db: Session):
        self.db = db

    def sync_activities(self, user_id: str, provider_name: str, records: List[ExternalActivityRecord]) -> Tuple[int, int, int]:
        """
        Synchronizes external records into the ActivityLog.
        Returns a tuple: (imported_count, updated_count, skipped_count).
        """
        if not records:
            return (0, 0, 0)
            
        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        if not profile:
            raise ValueError("HealthProfile not found")

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        for record in records:
            # Idempotency check: look for an existing record with the same external_record_id
            existing = self.db.query(ActivityLog).filter(
                ActivityLog.health_profile_id == profile.id,
                ActivityLog.external_record_id == record.external_record_id
            ).first()
            
            # Simple conflict resolution: do not overwrite manual data if it lands on the same day
            # with roughly the same activity type (for brevity, just doing ID duplication check here)
            
            if existing:
                # If it already exists and is from WEARABLE/IMPORTED, we could update it
                if existing.source in [ActivitySource.WEARABLE, ActivitySource.IMPORTED]:
                    existing.duration_minutes = record.duration_minutes
                    existing.steps = record.steps
                    existing.distance_km = record.distance_km
                    # Not overwriting manual estimates unless necessary
                    if not existing.estimated_calories_burned and record.active_calories:
                        existing.estimated_calories_burned = record.active_calories
                    existing.synced_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # It's a manual record that matched (unlikely given ID, but for safety)
                    skipped_count += 1
            else:
                # Insert new
                new_log = ActivityLog(
                    id=str(uuid.uuid4()),
                    health_profile_id=profile.id,
                    activity_date=record.start_time.date(),
                    activity_type=record.activity_type,
                    duration_minutes=record.duration_minutes,
                    steps=record.steps,
                    distance_km=record.distance_km,
                    estimated_calories_burned=record.active_calories or 0.0,
                    source=ActivitySource.IMPORTED,
                    external_source=provider_name,
                    external_record_id=record.external_record_id,
                    synced_at=datetime.utcnow()
                )
                self.db.add(new_log)
                imported_count += 1
                
        self.db.commit()
        return (imported_count, updated_count, skipped_count)
