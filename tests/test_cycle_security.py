import pytest
from datetime import date
from unittest.mock import Mock, patch
from fastapi import HTTPException
from app.services.cycle_service import CycleService
from app.models.health_profile import HealthProfile
from app.domain.health.privacy import HealthPrivacyGate
from app.domain.health.feature_policy import HealthFeaturePolicy

@pytest.fixture
def db_session_mock():
    return Mock()

@pytest.fixture
def cycle_service(db_session_mock):
    with patch("app.services.cycle_service.HealthProfileRepository") as mock_health_repo, \
         patch("app.services.cycle_service.PeriodLogRepository"), \
         patch("app.services.cycle_service.MenstrualCycleRepository"), \
         patch("app.services.cycle_service.CyclePredictionRepository"):
        service = CycleService(db_session_mock)
        service._health_repo_mock = mock_health_repo.return_value
        yield service

# 1. Missing Health Profile
def test_assert_cycle_access_no_profile(cycle_service):
    cycle_service._health_repo_mock.get_by_user_id.return_value = None
    
    with pytest.raises(HTTPException) as exc:
        cycle_service._assert_cycle_access("user_123")
    assert exc.value.status_code == 404
    assert "Health profile required" in str(exc.value.detail)

# 2. Underage user (< 14)
def test_assert_cycle_access_underage(cycle_service):
    # Today - 10 years
    dob = date.today().replace(year=date.today().year - 10)
    profile = HealthProfile(
        id="profile_123",
        user_id="user_123",
        date_of_birth=dob,
        cycle_tracking_enabled=True,
    )
    cycle_service._health_repo_mock.get_by_user_id.return_value = profile
    
    with pytest.raises(HTTPException) as exc:
        cycle_service._assert_cycle_access("user_123")
    assert exc.value.status_code == 403

# 3. Cycle tracking disabled in profile
def test_assert_cycle_access_disabled_preference(cycle_service):
    # Today - 20 years
    dob = date.today().replace(year=date.today().year - 20)
    profile = HealthProfile(
        id="profile_123",
        user_id="user_123",
        date_of_birth=dob,
        cycle_tracking_enabled=False,
    )
    cycle_service._health_repo_mock.get_by_user_id.return_value = profile
    
    with pytest.raises(HTTPException) as exc:
        cycle_service._assert_cycle_access("user_123")
    assert exc.value.status_code == 403

# 4. Valid access (Adult, enabled)
def test_assert_cycle_access_valid(cycle_service):
    dob = date.today().replace(year=date.today().year - 25)
    profile = HealthProfile(
        id="profile_123",
        user_id="user_123",
        date_of_birth=dob,
        cycle_tracking_enabled=True,
    )
    cycle_service._health_repo_mock.get_by_user_id.return_value = profile
    
    # Should not raise
    returned_profile = cycle_service._assert_cycle_access("user_123")
    assert returned_profile == profile
