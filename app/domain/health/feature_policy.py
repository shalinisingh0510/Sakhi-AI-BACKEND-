"""Centralized HealthFeaturePolicy — the single source of truth for feature access.

Instead of scattering `if age >= 18` checks throughout the codebase, all
feature-access decisions are made here by composing AgePolicy, HealthPrivacyGate,
and the user's stored preferences.

Usage::

    policy = HealthFeaturePolicy.build(
        age_policy=AgePolicy.from_dob(profile.date_of_birth),
        profile=profile,
    )
    if not policy.can_use_cycle_tracking():
        raise HTTPException(403, "Cycle tracking is not available.")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.health.age_policy import AgePolicy

if TYPE_CHECKING:
    from app.models.health_profile import HealthProfile


@dataclass(frozen=True)
class HealthFeaturePolicy:
    """Immutable policy snapshot for a single request.

    Never mutate — always create a new instance per request.
    """

    _age_policy: AgePolicy
    _cycle_tracking_pref: bool
    _nutrition_tracking_pref: bool
    _activity_tracking_pref: bool
    _ai_personalization_pref: bool

    @classmethod
    def build(
        cls,
        *,
        age_policy: AgePolicy,
        profile: "HealthProfile | None" = None,
    ) -> "HealthFeaturePolicy":
        """Build a policy from an age policy and optional stored preferences."""
        if profile is not None:
            return cls(
                _age_policy=age_policy,
                _cycle_tracking_pref=profile.cycle_tracking_enabled,
                _nutrition_tracking_pref=profile.nutrition_tracking_enabled,
                _activity_tracking_pref=profile.activity_tracking_enabled,
                _ai_personalization_pref=profile.ai_health_personalization_enabled,
            )
        # No profile yet (e.g. during initial profile creation)
        return cls(
            _age_policy=age_policy,
            _cycle_tracking_pref=True,
            _nutrition_tracking_pref=True,
            _activity_tracking_pref=True,
            _ai_personalization_pref=False,
        )

    # -- Feature gate methods ------------------------------------------------

    def can_use_cycle_tracking(self) -> bool:
        """Age 14+ AND user preference enabled."""
        return self._age_policy.can_use_cycle_tracking() and self._cycle_tracking_pref

    def can_use_nutrition_tracking(self) -> bool:
        return self._age_policy.can_use_nutrition_tracking() and self._nutrition_tracking_pref

    def can_use_activity_tracking(self) -> bool:
        return self._activity_tracking_pref

    def can_use_weight_features(self) -> bool:
        """Adult-only (18+)."""
        return self._age_policy.can_use_weight_features()

    def can_use_calorie_features(self) -> bool:
        """Adult-only (18+)."""
        return self._age_policy.can_use_calorie_deficit_features()

    def can_use_advanced_reproductive_features(self) -> bool:
        """Ovulation/fertility — adult-only (18+)."""
        return self._age_policy.can_use_advanced_health_features()

    def can_use_ai_health_personalization(self) -> bool:
        """Adult AND explicit opt-in stored in profile."""
        return (
            self._age_policy.can_use_ai_health_personalization()
            and self._ai_personalization_pref
        )

    @property
    def age_band(self) -> str:
        return self._age_policy.age_band
