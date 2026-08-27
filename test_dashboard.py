import sys
from datetime import date
from sqlalchemy import text
from app.db.session import init_db, get_session_factory
from app.core.config import get_settings
from app.services.wellness_dashboard_service import WellnessDashboardService

def test_dashboard():
    settings = get_settings()
    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    # Get all users
    users = db.execute(text("SELECT id FROM users")).fetchall()
    if not users:
        print("No users")
        return
        
    dashboard_service = WellnessDashboardService(db)
    
    for user in users:
        user_id = user[0]
        try:
            print(f"Testing dashboard for user {user_id}...")
            resp = dashboard_service.get_dashboard(user_id, date.today())
            print(f"Success! is_complete: {resp.profile.is_complete}")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_dashboard()
