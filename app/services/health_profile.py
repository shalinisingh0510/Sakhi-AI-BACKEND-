"""Health Profile service — orchestration layer.

Responsibilities:
  * Age validation (server-side, via AgePolicy.from_dob)
  * Profile creation / retrieval / update / deletion
  * Health condition management
  * Ownership enforcement (via HealthPrivacyGate)
  * Feature policy decisions (via HealthFeaturePolicy)
  * Transaction management (via transactional context)

Sensitive values (weight, conditions, allergies) are NEVER written to logs.
Log messages reference only user_id and operation type.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.domain.health.age_policy import AgePolicy
from app.domain.health.feature_policy import HealthFeaturePolicy
from app.domain.health.privacy import HealthPrivacyGate
from app.models.health_profile import HealthCondition, HealthProfile
from app.repositories.health import HealthConditionRepository, HealthProfileRepository
from app.schemas.health_profile import (
    HealthConditionCreate,
    HealthConditionResponse,
    HealthPermissionsUpdate,
    HealthProfileCreate,
    HealthProfileResponse,
    HealthProfileUpdate,
)

logger = logging.getLogger("sakhi.health")


class HealthProfileError(Exception):
    """Base exception for health profile operations."""


class ProfileNotFoundError(HealthProfileError):
    pass


class ProfileAlreadyExistsError(HealthProfileError):
    pass


class AgeEligibilityError(HealthProfileError):
    pass


class ConditionNotFoundError(HealthProfileError):
    pass


class HealthProfileService:
    """Orchestrates health profile lifecycle.

    Injected with a SQLAlchemy Session per request.  No business logic
    should bypass this service and query the DB directly.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._profile_repo = HealthProfileRepository(db)
        self._condition_repo = HealthConditionRepository(db)

    # -- Profile retrieval ---------------------------------------------------

    def get_profile(self, *, authenticated_user_id: str) -> HealthProfileResponse:
        """Return the profile for the authenticated user.

        Raises:
            ProfileNotFoundError: if no profile exists yet.
        """
        profile = self._profile_repo.get_by_user_id(authenticated_user_id)
        if profile is None:
            raise ProfileNotFoundError(
                f"No health profile found for user {authenticated_user_id}."
            )

        # Ownership is implicit: we queried by authenticated_user_id.
        logger.info("health_profile.retrieved user=%s", authenticated_user_id)
        return self._to_response(profile)

    # -- Profile creation ----------------------------------------------------

    def create_profile(
        self,
        *,
        authenticated_user_id: str,
        data: HealthProfileCreate,
    ) -> HealthProfileResponse:
        """Create a new health profile.

        Validates age server-side.  Rejects users under 14.
        Rejects if a profile already exists.

        Raises:
            ProfileAlreadyExistsError: if profile already exists.
            AgeEligibilityError: if user is under the minimum age.
        """
        if self._profile_repo.user_has_profile(authenticated_user_id):
            raise ProfileAlreadyExistsError(
                "A health profile already exists. Use PATCH to update it."
            )

        # Server-side age validation — never trust the client.
        age_policy = AgePolicy.from_dob(data.date_of_birth)
        if not age_policy.is_health_hub_allowed():
            raise AgeEligibilityError(
                "Sakhi Health Hub is available for users aged 14 and older."
            )

        logger.info(
            "health_profile.creating user=%s age_band=%s",
            authenticated_user_id,
            age_policy.age_band,
        )

        with transactional(self._db):
            profile = HealthProfile(
                id=str(uuid4()),
                user_id=authenticated_user_id,
                date_of_birth=data.date_of_birth,
                biological_sex=getattr(data, "biological_sex", None),
                height_cm=data.height_cm,
                weight_kg=data.weight_kg,
                activity_level=data.activity_level.value,
                diet_type=data.diet_type.value,
                cycle_tracking_enabled=data.cycle_tracking_enabled,
                nutrition_tracking_enabled=data.nutrition_tracking_enabled,
                activity_tracking_enabled=data.activity_tracking_enabled,
                ai_health_personalization_enabled=data.ai_health_personalization_enabled,
            )
            profile.food_allergies = data.food_allergies
            profile.dietary_restrictions = data.dietary_restrictions

            self._profile_repo.add(profile)

        logger.info("health_profile.created user=%s", authenticated_user_id)
        return self._to_response(profile)

    # -- Profile update ------------------------------------------------------

    def update_profile(
        self,
        *,
        authenticated_user_id: str,
        data: HealthProfileUpdate,
    ) -> HealthProfileResponse:
        """Partial update of the health profile."""
        profile = self._profile_repo.get_by_user_id(authenticated_user_id)
        if profile is None:
            raise ProfileNotFoundError("Health profile not found.")

        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id=authenticated_user_id, profile=profile
        )
        gate.assert_owner(profile.user_id)

        with transactional(self._db):
            if data.height_cm is not None:
                profile.height_cm = data.height_cm
            if data.weight_kg is not None:
                profile.weight_kg = data.weight_kg
            if data.activity_level is not None:
                profile.activity_level = data.activity_level.value
            if data.diet_type is not None:
                profile.diet_type = data.diet_type.value
            if data.food_allergies is not None:
                profile.food_allergies = data.food_allergies
            if data.dietary_restrictions is not None:
                profile.dietary_restrictions = data.dietary_restrictions
            if data.cycle_tracking_enabled is not None:
                profile.cycle_tracking_enabled = data.cycle_tracking_enabled
            if data.nutrition_tracking_enabled is not None:
                profile.nutrition_tracking_enabled = data.nutrition_tracking_enabled
            if data.activity_tracking_enabled is not None:
                profile.activity_tracking_enabled = data.activity_tracking_enabled
            if data.ai_health_personalization_enabled is not None:
                profile.ai_health_personalization_enabled = (
                    data.ai_health_personalization_enabled
                )
            if hasattr(data, "biological_sex") and data.biological_sex is not None:
                profile.biological_sex = data.biological_sex

        logger.info("health_profile.updated user=%s", authenticated_user_id)
        return self._to_response(profile)

    # -- Permissions update --------------------------------------------------

    def update_permissions(
        self,
        *,
        authenticated_user_id: str,
        data: HealthPermissionsUpdate,
    ) -> HealthProfileResponse:
        """Update only the tracking permission flags."""
        update = HealthProfileUpdate(
            cycle_tracking_enabled=data.cycle_tracking_enabled,
            nutrition_tracking_enabled=data.nutrition_tracking_enabled,
            activity_tracking_enabled=data.activity_tracking_enabled,
            ai_health_personalization_enabled=data.ai_health_personalization_enabled,
        )
        return self.update_profile(authenticated_user_id=authenticated_user_id, data=update)

    # -- Conditions ----------------------------------------------------------

    def get_conditions(
        self, *, authenticated_user_id: str
    ) -> list[HealthConditionResponse]:
        """Return all self-reported conditions for the user."""
        conditions = self._condition_repo.list_by_user_id(authenticated_user_id)
        return [self._condition_to_response(c) for c in conditions]

    def add_condition(
        self,
        *,
        authenticated_user_id: str,
        data: HealthConditionCreate,
    ) -> HealthConditionResponse:
        """Add a self-reported health condition."""
        with transactional(self._db):
            condition = HealthCondition(
                id=str(uuid4()),
                user_id=authenticated_user_id,
                condition_code=data.condition_code.value,
                display_name=data.display_name,
                status="self_reported",
                notes=data.notes,
                reported_at=datetime.now(timezone.utc),
            )
            self._condition_repo.add(condition)

        # NOTE: We do NOT log condition_code or display_name — sensitive health data.
        logger.info("health_condition.added user=%s", authenticated_user_id)
        return self._condition_to_response(condition)

    def remove_condition(
        self,
        *,
        authenticated_user_id: str,
        condition_id: str,
    ) -> None:
        """Remove a self-reported health condition."""
        condition = self._condition_repo.get_by_id_and_user(
            condition_id, authenticated_user_id
        )
        if condition is None:
            raise ConditionNotFoundError("Condition not found.")

        with transactional(self._db):
            self._condition_repo.delete(condition)

        logger.info("health_condition.removed user=%s", authenticated_user_id)

    # -- Helpers -------------------------------------------------------------

    def _to_response(self, profile: HealthProfile) -> HealthProfileResponse:
        age_policy = AgePolicy.from_dob(profile.date_of_birth)
        feature_policy = HealthFeaturePolicy.build(
            age_policy=age_policy, profile=profile
        )
        return HealthProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            date_of_birth=profile.date_of_birth,
            biological_sex=profile.biological_sex,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            activity_level=profile.activity_level,
            diet_type=profile.diet_type,
            food_allergies=profile.food_allergies,
            dietary_restrictions=profile.dietary_restrictions,
            cycle_tracking_enabled=bool(profile.cycle_tracking_enabled),
            nutrition_tracking_enabled=bool(profile.nutrition_tracking_enabled),
            activity_tracking_enabled=bool(profile.activity_tracking_enabled),
            ai_health_personalization_enabled=bool(profile.ai_health_personalization_enabled),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            age_band=feature_policy.age_band,
            is_health_hub_allowed=age_policy.is_health_hub_allowed(),
        )

    @staticmethod
    def _condition_to_response(c: HealthCondition) -> HealthConditionResponse:
        return HealthConditionResponse(
            id=c.id,
            user_id=c.user_id,
            condition_code=c.condition_code,
            display_name=c.display_name,
            status=c.status,
            reported_at=c.reported_at,
            created_at=c.created_at,
        )
