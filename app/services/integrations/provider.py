from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class ExternalActivityRecord(BaseModel):
    """
    Standardized payload for external activities imported from providers.
    """
    external_record_id: str
    activity_type: str
    start_time: datetime
    duration_minutes: int
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    active_calories: Optional[float] = None
    
class HealthProviderAdapter(Protocol):
    """
    Protocol for integration adapters (e.g., Google Fit, Apple Health).
    """
    @property
    def provider_type(self) -> str:
        """Returns the ProviderType enum string for this adapter."""
        ...
        
    def authenticate(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges an auth code for access/refresh tokens.
        Returns a dict of token data to be stored securely.
        """
        ...
        
    def revoke_access(self, token_data: Dict[str, Any]) -> bool:
        """
        Revokes the user's access token at the provider.
        """
        ...
        
    def fetch_activities(
        self, 
        token_data: Dict[str, Any], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ExternalActivityRecord]:
        """
        Fetches activity data from the provider between the specified dates.
        Must handle its own pagination and rate limits.
        """
        ...
