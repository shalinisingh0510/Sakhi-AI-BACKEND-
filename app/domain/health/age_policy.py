"""Age-based health feature policy — server-side enforcement.

All age-sensitive feature gates MUST be checked server-side via this
class.  Frontend may additionally hide UI elements, but the backend is
the authoritative enforcement layer.

Phase 0: Extension point only — default policies allow all features for
users 14+.  Final policy decisions will be made in Phase 1.
"""

from __future__ import annotations

from app.domain.health.constants import ADULT_AGE_MIN, TEEN_AGE_MAX, TEEN_AGE_MIN


class AgePolicy:
    """Server-side age-based feature gating.

    Instantiated with the user's age (or age group string).  Methods
    return whether the user is permitted to access specific health
    features.

    Example::

        policy = AgePolicy(age=15)
        if not policy.can_use_cycle_tracking():
            raise HTTPException(403, "Feature not available for your age group.")
    """

    def __init__(self, *, age: int | None = None, age_group: str | None = None) -> None:
        self._age = age
        self._age_group = age_group

        # Resolve age from age_group if age not given directly.
        if self._age is None and self._age_group is not None:
            self._age = self._resolve_age_from_group(self._age_group)

    @staticmethod
    def _resolve_age_from_group(group: str) -> int | None:
        """Map the frontend age-group strings to a representative age."""
        mapping: dict[str, int] = {
            "10-13": 12,
            "14-18": 16,
            "18+": 25,
            "caregiver": 30,
        }
        return mapping.get(group.strip().lower())

    @property
    def is_teen(self) -> bool:
        if self._age is None:
            return False
        return TEEN_AGE_MIN <= self._age <= TEEN_AGE_MAX

    @property
    def is_adult(self) -> bool:
        if self._age is None:
            return True  # default permissive
        return self._age >= ADULT_AGE_MIN

    # -- Feature gates --------------------------------------------------------
    # Phase 0: All return True.  Phase 1 will refine these.

    def can_use_cycle_tracking(self) -> bool:
        """Users 14+ may use cycle tracking."""
        if self._age is None:
            return True
        return self._age >= TEEN_AGE_MIN

    def can_use_nutrition_tracking(self) -> bool:
        """Users 14+ may use nutrition tracking."""
        if self._age is None:
            return True
        return self._age >= TEEN_AGE_MIN

    def can_use_weight_features(self) -> bool:
        """Weight tracking is adult-only (18+)."""
        return self.is_adult

    def can_use_calorie_deficit_features(self) -> bool:
        """Calorie deficit / restrictive diet features are adult-only."""
        return self.is_adult

    def can_use_advanced_health_features(self) -> bool:
        """Advanced features (ovulation estimate, etc.) are adult-only."""
        return self.is_adult
