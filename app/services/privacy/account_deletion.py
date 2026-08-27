from sqlalchemy.orm import Session

from app.models.health_profile import HealthProfile
from app.models.wellness_plan import WellnessGoal, WellnessPlan
from app.models.integrations import HealthProviderConnection, ExternalSyncLog
# In a real environment, we'd also import the core User model to delete the account entirely.
# We'll just delete the health profile for Phase 16, relying on CASCADE deletes for the logs.

class AccountDeletionService:
    """
    Handles permanent account and health data deletion (Right to be Forgotten).
    Cascades delete operations across all related stores.
    """
    def __init__(self, db: Session):
        self.db = db

    def delete_account(self, user_id: str) -> bool:
        """
        Deletes all health data associated with the user_id.
        """
        try:
            # 1. Delete Integrations (and sync logs via cascade if set up, or manually here)
            connections = self.db.query(HealthProviderConnection).filter(HealthProviderConnection.user_id == user_id).all()
            for conn in connections:
                self.db.query(ExternalSyncLog).filter(ExternalSyncLog.connection_id == conn.id).delete()
                self.db.delete(conn)
                
            # 2. Delete Wellness Plans and Goals
            self.db.query(WellnessPlan).filter(WellnessPlan.user_id == user_id).delete()
            self.db.query(WellnessGoal).filter(WellnessGoal.user_id == user_id).delete()
            
            # 3. Delete Health Profile
            # Note: The health_profiles table is configured with ondelete="CASCADE" 
            # for activity, nutrition, cycle, symptom, mood, and energy logs.
            # Deleting the profile automatically drops all associated logs.
            profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
            if profile:
                self.db.delete(profile)
                
            # 4. In a real system: Delete the auth User, revoke tokens, drop from Redis
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to delete account data: {e}")
