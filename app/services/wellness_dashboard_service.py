from datetime import date, timedelta
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.schemas.dashboard import (
    WellnessDashboardResponse, DashboardProfileSnapshot, TodaySnapshot,
    CycleSnapshot, WellnessTrendsSnapshot, TrackingStatusSnapshot
)
from app.services.health_profile import HealthProfileService
from app.services.wellness_service import WellnessService
from app.services.cycle_service import CycleService
from app.repositories.wellness import SymptomLogRepository, MoodLogRepository, EnergyLogRepository
from app.repositories.cycle import MenstrualCycleRepository

class WellnessDashboardService:
    def __init__(self, db: Session):
        self._db = db
        self._profile_service = HealthProfileService(db)
        self._wellness_service = WellnessService(db)
        self._cycle_service = CycleService(db)
        self._symptom_repo = SymptomLogRepository(db)
        self._mood_repo = MoodLogRepository(db)
        self._energy_repo = EnergyLogRepository(db)
        self._cycle_repo = MenstrualCycleRepository(db)

    def get_dashboard(self, user_id: str, local_date: date) -> WellnessDashboardResponse:
        try:
            profile = self._profile_service.get_profile(authenticated_user_id=user_id)
            is_complete = True
        except Exception:
            profile = None
            is_complete = False
            
        mode = "teen" if (profile and profile.age_band == "teen") else "adult"

        if not is_complete:
            # Return empty state if profile is incomplete
            return WellnessDashboardResponse(
                date=local_date,
                profile=DashboardProfileSnapshot(is_complete=False, mode="adult"),
                today=TodaySnapshot(check_in_completed=False),
                cycle=CycleSnapshot(),
                trends=WellnessTrendsSnapshot(),
                tracking_status=TrackingStatusSnapshot(
                    check_in_status="Not tracked",
                    cycle_status="Not tracked",
                    symptoms_status="Not tracked"
                )
            )

        # 1. Today Snapshot
        today_symptoms = self._symptom_repo.list_by_profile_and_date(profile.id, local_date)
        
        today_mood = self._mood_repo.get_by_profile_and_date(profile.id, local_date)
        today_energy = self._energy_repo.get_by_profile_and_date(profile.id, local_date)

        check_in_completed = bool(today_mood or today_energy or today_symptoms)
        
        today_snapshot = TodaySnapshot(
            check_in_completed=check_in_completed,
            mood=today_mood.mood_code if today_mood else None,
            energy=today_energy.energy_level if today_energy else None,
            symptoms_count=len(today_symptoms),
            symptoms=[{"symptom_code": s.symptom_code, "severity": s.severity} for s in today_symptoms]
        )

        # 2. Cycle Snapshot
        cycle_snapshot = CycleSnapshot()
        if profile.cycle_tracking_enabled:
            # Try to determine current cycle day using WellnessService's robust matcher
            cycle_id, cycle_day = self._wellness_service._determine_cycle(profile.id, local_date)
            
            # Fetch latest predictions via CycleService
            # (Note: cycle_service.get_predictions requires a valid cycle ID and logic, we use standard logic here)
            active_cycles = self._cycle_repo.list_all_by_profile(profile.id)
            if active_cycles:
                active_cycles.sort(key=lambda c: c.cycle_start_date, reverse=True)
                current_cycle = active_cycles[0]
                
                if not cycle_id and current_cycle.cycle_end_date is None:
                    cycle_day = (local_date - current_cycle.cycle_start_date).days + 1
                    
                cycle_snapshot.cycle_day = cycle_day
                
                # Fetch prediction stats
                stats = self._cycle_service.get_statistics(user_id)
                
                if current_cycle.cycle_start_date:
                    cycle_len = stats.average_cycle_length or 28
                    # Approximate estimates for dashboard view
                    next_period_estimate = current_cycle.cycle_start_date + timedelta(days=cycle_len)
                    if local_date <= next_period_estimate:
                         cycle_snapshot.next_period = next_period_estimate
                         cycle_snapshot.ovulation = next_period_estimate - timedelta(days=14)
                    
                    cycle_snapshot.confidence = "HIGH" if stats.total_cycles_tracked >= 3 else "LIMITED"

        # 3. Trends (Simplistic query for dashboard)
        # In a real heavy-load scenario we'd use optimized GROUP BY queries, but for Phase 4 python processing is fine.
        symptom_logs = self._symptom_repo.list_by_profile(profile.id, limit=500)
        thirty_days_ago = local_date - timedelta(days=30)
        seven_days_ago = local_date - timedelta(days=7)
        
        recent_symptom_days = len(set(s.start_date for s in symptom_logs if s.start_date >= thirty_days_ago))
        
        # Approximate check-ins (since we don't have a check-in table, count unique dates with mood/energy/symptoms)
        mood_logs = self._mood_repo.list_by_profile(profile.id, limit=30)
        energy_logs = self._energy_repo.list_by_profile(profile.id, limit=30)
        
        checkin_dates_30 = set()
        checkin_dates_7 = set()
        
        for m in mood_logs:
            if m.log_date >= thirty_days_ago: checkin_dates_30.add(m.log_date)
            if m.log_date >= seven_days_ago: checkin_dates_7.add(m.log_date)
            
        for e in energy_logs:
            if e.log_date >= thirty_days_ago: checkin_dates_30.add(e.log_date)
            if e.log_date >= seven_days_ago: checkin_dates_7.add(e.log_date)
            
        for s in symptom_logs:
            if s.start_date >= thirty_days_ago: checkin_dates_30.add(s.start_date)
            if s.start_date >= seven_days_ago: checkin_dates_7.add(s.start_date)

        trends = WellnessTrendsSnapshot(
            symptom_days_last_30=recent_symptom_days,
            check_ins_last_7=len(checkin_dates_7),
            check_ins_last_30=len(checkin_dates_30)
        )

        # 4. Tracking Status
        status = TrackingStatusSnapshot(
            check_in_status="Completed" if check_in_completed else "Pending",
            cycle_status="Tracked" if cycle_snapshot.cycle_day else "Not Tracked",
            symptoms_status="Logged" if today_symptoms else "No Symptoms"
        )

        return WellnessDashboardResponse(
            date=local_date,
            profile=DashboardProfileSnapshot(is_complete=is_complete, mode=mode),
            today=today_snapshot,
            cycle=cycle_snapshot,
            trends=trends,
            tracking_status=status
        )
