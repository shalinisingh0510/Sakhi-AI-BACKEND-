import pytest
from datetime import date
from unittest.mock import Mock, patch
from app.services.wellness_service import WellnessService
from app.models.menstrual_cycle import MenstrualCycle
from app.models.health_profile import HealthProfile

@pytest.fixture
def db_session_mock():
    return Mock()

@pytest.fixture
def wellness_service(db_session_mock):
    with patch("app.services.wellness_service.HealthProfileRepository"), \
         patch("app.services.wellness_service.SymptomLogRepository"), \
         patch("app.services.wellness_service.MoodLogRepository"), \
         patch("app.services.wellness_service.EnergyLogRepository"), \
         patch("app.services.wellness_service.MenstrualCycleRepository") as mock_cycle_repo:
        service = WellnessService(db_session_mock)
        service._cycle_repo_mock = mock_cycle_repo.return_value
        yield service

# 1. Test Cycle Determination (Inside Cycle)
def test_determine_cycle_inside(wellness_service):
    # Active cycle: Aug 1 to Aug 28
    c = MenstrualCycle(
        id="cycle_123",
        health_profile_id="profile_1",
        cycle_start_date=date(2026, 8, 1),
        cycle_end_date=date(2026, 8, 28)
    )
    wellness_service._cycle_repo.list_all_by_profile.return_value = [c]
    
    # Symptom logged on Aug 10
    cycle_id, cycle_day = wellness_service._determine_cycle("profile_1", date(2026, 8, 10))
    
    assert cycle_id == "cycle_123"
    assert cycle_day == 10 # Aug 1 is Day 1

# 2. Test Cycle Determination (Current Incomplete Cycle)
def test_determine_cycle_incomplete(wellness_service):
    # Current cycle: started Aug 1, end is None
    c = MenstrualCycle(
        id="cycle_456",
        health_profile_id="profile_1",
        cycle_start_date=date(2026, 8, 1),
        cycle_end_date=None
    )
    wellness_service._cycle_repo.list_all_by_profile.return_value = [c]
    
    cycle_id, cycle_day = wellness_service._determine_cycle("profile_1", date(2026, 8, 23))
    
    assert cycle_id == "cycle_456"
    assert cycle_day == 23

# 3. Test Cycle Determination (Outside any cycle)
def test_determine_cycle_outside(wellness_service):
    c = MenstrualCycle(
        id="cycle_789",
        health_profile_id="profile_1",
        cycle_start_date=date(2026, 8, 1),
        cycle_end_date=date(2026, 8, 28)
    )
    wellness_service._cycle_repo.list_all_by_profile.return_value = [c]
    
    # Symptom logged July 20 (before any tracked cycle)
    cycle_id, cycle_day = wellness_service._determine_cycle("profile_1", date(2026, 7, 20))
    
    assert cycle_id is None
    assert cycle_day is None
