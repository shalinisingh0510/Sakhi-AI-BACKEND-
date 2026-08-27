from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid
import random

from app.models.integrations import ProviderType
from app.services.integrations.provider import HealthProviderAdapter, ExternalActivityRecord

class GoogleFitAdapter(HealthProviderAdapter):
    """
    Mock integration for Google Fit / Health Connect.
    In a real environment, this would use google-api-python-client.
    """
    @property
    def provider_type(self) -> str:
        return ProviderType.GOOGLE_HEALTH_CONNECT.value

    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Mock OAuth exchange.
        """
        return {
            "access_token": f"mock_access_{uuid.uuid4().hex}",
            "refresh_token": f"mock_refresh_{uuid.uuid4().hex}",
            "expires_in": 3600,
            "provider_user_id": f"gfit_{random.randint(1000, 9999)}"
        }

    def revoke_access(self, token_data: Dict[str, Any]) -> bool:
        """
        Mock revocation.
        """
        return True

    def fetch_activities(
        self, 
        token_data: Dict[str, Any], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ExternalActivityRecord]:
        """
        Mock fetching data from Google Fit.
        Generates 1-2 realistic-looking activities per day.
        """
        records = []
        current_date = start_date
        
        while current_date <= end_date:
            # 50% chance of a walking workout
            if random.random() > 0.5:
                records.append(ExternalActivityRecord(
                    external_record_id=f"gfit_walk_{current_date.strftime('%Y%m%d')}",
                    activity_type="WALKING",
                    start_time=current_date.replace(hour=8, minute=0, second=0),
                    duration_minutes=random.randint(15, 60),
                    steps=random.randint(2000, 5000),
                    distance_km=round(random.uniform(1.0, 4.0), 2),
                    active_calories=random.randint(100, 300)
                ))
            current_date += timedelta(days=1)
            
        return records
