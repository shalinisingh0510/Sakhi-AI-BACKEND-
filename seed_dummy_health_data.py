import sys
from datetime import date, timedelta
from sqlalchemy import text
from app.db.session import init_db, get_session_factory
from app.core.config import get_settings

def seed_data():
    settings = get_settings()
    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    # Get all users
    users = db.execute(text("SELECT id FROM users")).fetchall()
    if not users:
        print("No users found in the database. Please create a user first.")
        return

    print(f"Found {len(users)} users. Seeding dummy health data...")
    
    today = date.today()
    
    for user in users:
        user_id = user[0]
        
        # 1. Create Health Profile
        db.execute(text("""
            INSERT INTO health_profiles (
                id, user_id, date_of_birth, biological_sex, height_cm, weight_kg, 
                activity_level, diet_type, ai_health_personalization_enabled, 
                cycle_tracking_enabled, created_at, updated_at
            ) VALUES (
                gen_random_uuid()::text, :user_id, '1995-05-15', 'FEMALE', 165.0, 60.0,
                'MODERATE', 'VEGETARIAN', TRUE, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (user_id) DO NOTHING
        """), {"user_id": user_id})
        
        # Get the profile ID we just created or that already existed
        profile = db.execute(text("SELECT id FROM health_profiles WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        if not profile:
            continue
        profile_id = profile[0]

        # 2. Add some daily checkins (Mood & Energy) for today
        db.execute(text("""
            INSERT INTO mood_logs (id, health_profile_id, log_date, mood_code, intensity, notes, created_at)
            VALUES (gen_random_uuid()::text, :profile_id, :today, 'CALM', 'MILD', 'Feeling good today', CURRENT_TIMESTAMP)
        """), {"profile_id": profile_id, "today": today.isoformat()})
        
        db.execute(text("""
            INSERT INTO energy_logs (id, health_profile_id, log_date, energy_level, notes, created_at)
            VALUES (gen_random_uuid()::text, :profile_id, :today, 'HIGH', 'Slept well', CURRENT_TIMESTAMP)
        """), {"profile_id": profile_id, "today": today.isoformat()})

        # 3. Add a symptom
        db.execute(text("""
            INSERT INTO symptom_logs (id, health_profile_id, start_date, symptom_code, category, severity, created_at, updated_at)
            VALUES (gen_random_uuid()::text, :profile_id, :today, 'cramps', 'physical', 'MILD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"profile_id": profile_id, "today": today.isoformat()})

        # 4. Add a menstrual cycle
        cycle_start = today - timedelta(days=5)
        db.execute(text("""
            INSERT INTO menstrual_cycles (id, health_profile_id, cycle_start_date, cycle_end_date, created_at, updated_at)
            VALUES (gen_random_uuid()::text, :profile_id, :cycle_start, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """), {"profile_id": profile_id, "cycle_start": cycle_start.isoformat()})

        # 5. Add a wellness plan
        db.execute(text("""
            INSERT INTO wellness_plans (id, user_id, title, action_type, frequency, status, reasoning, created_at)
            VALUES (gen_random_uuid()::text, :user_id, 'Hydration & Energy', 'LOG_WATER', 'DAILY', 'ACCEPTED', 'Suggested based on your goals.', CURRENT_TIMESTAMP)
        """), {"user_id": user_id})

    db.commit()
    print("Dummy data successfully seeded!")

if __name__ == "__main__":
    seed_data()
