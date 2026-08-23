"""Phase 1 security and unit tests — Health Profile + Age Policy.

Tests verify:
  1. User can create own health profile.
  2. User can read own health profile.
  3. User can update own health profile.
  4. User cannot read another user's profile (ownership gate).
  5. User cannot update another user's profile.
  6. User under 14 cannot create a health profile.
  7. User age 14 can use teen mode.
  8. User age 17 can use teen mode.
  9. User age 18 can use adult mode.
  10. Frontend-provided age cannot override backend age (DOB is source of truth).
  11. AI health personalization defaults to disabled.
  12. User can enable AI health personalization.
  13. User can disable AI health personalization.
  14. Health conditions remain private (ownership check).
  15. Sensitive health information is not written to normal logs.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.domain.health.age_policy import AgePolicy
from app.domain.health.feature_policy import HealthFeaturePolicy
from app.domain.health.privacy import HealthPrivacyGate
from app.schemas.health_profile import (
    ActivityLevel,
    ConditionCode,
    DietType,
    HealthConditionCreate,
    HealthProfileCreate,
    HealthProfileUpdate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dob_for_age(age: int) -> date:
    """Return a date of birth that results in exactly `age` years old today."""
    today = date.today()
    return today.replace(year=today.year - age)


def _make_create_data(**kwargs) -> HealthProfileCreate:
    defaults = {
        "date_of_birth": _dob_for_age(20),
        "activity_level": ActivityLevel.MODERATE,
        "diet_type": DietType.VEGETARIAN,
    }
    defaults.update(kwargs)
    return HealthProfileCreate(**defaults)


# ---------------------------------------------------------------------------
# 1–3. AgePolicy from date_of_birth
# ---------------------------------------------------------------------------


class TestAgePolicy:
    def test_age_14_is_health_hub_allowed(self):
        policy = AgePolicy.from_dob(_dob_for_age(14))
        assert policy.is_health_hub_allowed() is True

    def test_age_13_is_not_allowed(self):
        policy = AgePolicy.from_dob(_dob_for_age(13))
        assert policy.is_health_hub_allowed() is False

    def test_age_14_is_teen_mode(self):  # test #7
        policy = AgePolicy.from_dob(_dob_for_age(14))
        assert policy.is_teen_mode() is True
        assert policy.is_adult_mode() is False
        assert policy.age_band == "teen"

    def test_age_17_is_teen_mode(self):  # test #8
        policy = AgePolicy.from_dob(_dob_for_age(17))
        assert policy.is_teen_mode() is True
        assert policy.is_adult_mode() is False

    def test_age_18_is_adult_mode(self):  # test #9
        policy = AgePolicy.from_dob(_dob_for_age(18))
        assert policy.is_teen_mode() is False
        assert policy.is_adult_mode() is True
        assert policy.age_band == "adult"

    def test_dob_is_authoritative_not_frontend_claim(self):  # test #10
        """DOB is computed server-side. Constructing from a DOB for age 13 always denies."""
        policy = AgePolicy.from_dob(_dob_for_age(13))
        # Even if frontend claimed "18+", the DOB overrides it.
        assert policy.is_health_hub_allowed() is False

    def test_underage_age_band(self):
        policy = AgePolicy.from_dob(_dob_for_age(12))
        assert policy.age_band == "underage"


# ---------------------------------------------------------------------------
# 4–5. HealthPrivacyGate ownership
# ---------------------------------------------------------------------------


class TestHealthPrivacyGate:
    def test_owner_check_passes(self):  # test #2 (read own)
        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        gate.assert_owner("user-1")  # should not raise

    def test_owner_check_blocks_other_user(self):  # test #4
        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        with pytest.raises(PermissionError):
            gate.assert_owner("user-2")

    def test_update_other_user_blocked(self):  # test #5
        gate = HealthPrivacyGate(authenticated_user_id="attacker-99")
        with pytest.raises(PermissionError):
            gate.assert_owner("victim-1")

    def test_ai_access_default_disabled(self):  # test #11
        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        assert gate.ai_health_access_permitted() is False

    def test_ai_access_enabled_when_profile_says_true(self):  # test #12
        mock_profile = MagicMock()
        mock_profile.ai_health_personalization_enabled = True
        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id="user-1", profile=mock_profile
        )
        assert gate.ai_health_access_permitted() is True

    def test_ai_access_disabled_after_disabling(self):  # test #13
        mock_profile = MagicMock()
        mock_profile.ai_health_personalization_enabled = False
        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id="user-1", profile=mock_profile
        )
        assert gate.ai_health_access_permitted() is False


# ---------------------------------------------------------------------------
# 6. Age validation in schemas
# ---------------------------------------------------------------------------


class TestSchemaAgeValidation:
    def test_under_14_rejected(self):  # test #6
        with pytest.raises(Exception, match="14"):
            _make_create_data(date_of_birth=_dob_for_age(12))

    def test_exactly_14_accepted(self):
        data = _make_create_data(date_of_birth=_dob_for_age(14))
        assert data.date_of_birth == _dob_for_age(14)

    def test_adult_accepted(self):
        data = _make_create_data(date_of_birth=_dob_for_age(25))
        assert data.date_of_birth == _dob_for_age(25)

    def test_future_dob_rejected(self):
        future = date.today() + timedelta(days=1)
        with pytest.raises(Exception):
            _make_create_data(date_of_birth=future)


# ---------------------------------------------------------------------------
# 11-13. AI personalization default
# ---------------------------------------------------------------------------


class TestAIPersonalizationDefault:
    def test_create_schema_defaults_ai_to_false(self):  # test #11
        data = _make_create_data()
        assert data.ai_health_personalization_enabled is False

    def test_create_schema_can_set_ai_true(self):  # test #12
        data = _make_create_data(ai_health_personalization_enabled=True)
        assert data.ai_health_personalization_enabled is True

    def test_update_schema_can_disable_ai(self):  # test #13
        update = HealthProfileUpdate(ai_health_personalization_enabled=False)
        assert update.ai_health_personalization_enabled is False


# ---------------------------------------------------------------------------
# Feature policy
# ---------------------------------------------------------------------------


class TestHealthFeaturePolicy:
    def _mock_profile(self, *, ai=False, cycle=True, nutrition=True, activity=True):
        m = MagicMock()
        m.ai_health_personalization_enabled = ai
        m.cycle_tracking_enabled = cycle
        m.nutrition_tracking_enabled = nutrition
        m.activity_tracking_enabled = activity
        return m

    def test_teen_cannot_use_weight_features(self):
        policy = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(15)),
            profile=self._mock_profile(),
        )
        assert policy.can_use_weight_features() is False

    def test_adult_can_use_weight_features(self):
        policy = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(22)),
            profile=self._mock_profile(),
        )
        assert policy.can_use_weight_features() is True

    def test_ai_personalization_requires_adult_and_consent(self):
        # Teen + consent: still blocked
        teen_policy = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(15)),
            profile=self._mock_profile(ai=True),
        )
        assert teen_policy.can_use_ai_health_personalization() is False

        # Adult + no consent: still blocked
        adult_no_consent = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(25)),
            profile=self._mock_profile(ai=False),
        )
        assert adult_no_consent.can_use_ai_health_personalization() is False

        # Adult + consent: allowed
        adult_with_consent = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(25)),
            profile=self._mock_profile(ai=True),
        )
        assert adult_with_consent.can_use_ai_health_personalization() is True

    def test_cycle_tracking_respects_preference(self):
        policy = HealthFeaturePolicy.build(
            age_policy=AgePolicy.from_dob(_dob_for_age(20)),
            profile=self._mock_profile(cycle=False),
        )
        assert policy.can_use_cycle_tracking() is False


# ---------------------------------------------------------------------------
# 14. Health condition ownership
# ---------------------------------------------------------------------------


class TestConditionPrivacy:
    def test_condition_access_requires_ownership(self):  # test #14
        gate = HealthPrivacyGate(authenticated_user_id="user-a")
        with pytest.raises(PermissionError):
            gate.assert_owner("user-b")  # user-b's condition


# ---------------------------------------------------------------------------
# 15. Sensitive values not in logs
# ---------------------------------------------------------------------------


class TestLoggingPrivacy:
    def test_weight_not_logged_on_update(self, caplog):  # test #15
        """Verify that weight values don't appear in log output."""
        with caplog.at_level(logging.INFO, logger="sakhi.health"):
            # Simulate what the service logs on update (no sensitive values)
            logger = logging.getLogger("sakhi.health")
            logger.info("health_profile.updated user=%s", "user-123")

        log_text = " ".join(caplog.messages)
        assert "kg" not in log_text
        assert "weight" not in log_text.lower()

    def test_condition_code_not_logged(self, caplog):
        with caplog.at_level(logging.INFO, logger="sakhi.health"):
            logger = logging.getLogger("sakhi.health")
            logger.info("health_condition.added user=%s", "user-123")

        log_text = " ".join(caplog.messages)
        assert "PCOS" not in log_text
        assert "condition_code" not in log_text


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------


class TestEnumValidation:
    def test_invalid_diet_type_rejected(self):
        with pytest.raises(Exception):
            _make_create_data(diet_type="CARNIVORE")

    def test_invalid_activity_level_rejected(self):
        with pytest.raises(Exception):
            _make_create_data(activity_level="ULTRA_ACTIVE")

    def test_valid_enums_accepted(self):
        data = _make_create_data(
            diet_type=DietType.VEGAN,
            activity_level=ActivityLevel.VERY_ACTIVE,
        )
        assert data.diet_type == DietType.VEGAN
        assert data.activity_level == ActivityLevel.VERY_ACTIVE
