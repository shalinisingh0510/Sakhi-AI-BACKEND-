import sys
import traceback
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
    
    users = db.execute(text("SELECT id FROM users")).fetchall()
    
    with open("dashboard_test_log.txt", "w") as f:
        if not users:
            f.write("No users\n")
            return
            
        dashboard_service = WellnessDashboardService(db)
        
        for user in users:
            user_id = user[0]
            try:
                f.write(f"Testing dashboard for user {user_id}...\n")
                resp = dashboard_service.get_dashboard(user_id, date.today())
                f.write(f"Success! is_complete: {resp.profile.is_complete}\n")
            except Exception as e:
                f.write(f"Error for user {user_id}: {e}\n")
                f.write(traceback.format_exc() + "\n")

if __name__ == "__main__":
    test_dashboard()
