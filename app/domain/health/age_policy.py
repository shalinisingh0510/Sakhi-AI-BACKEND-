"""Age-based health feature policy — server-side enforcement.

Phase 1 extensions:
  - AgePolicy can now be constructed from a date_of_birth for precise age calculation.
  - is_health_hub_allowed() added as the primary gate.
  - is_teen_mode() / is_adult_mode() added for UI branching decisions.
  - All future feature gates are wired here; they return False until their phase activates them.
"""

from __future__ import annotations

from datetime import date

from app.domain.health.constants import ADULT_AGE_MIN, HEALTH_HUB_MIN_AGE, TEEN_AGE_MAX, TEEN_AGE_MIN


class AgePolicy:
    """Server-side age-based feature gating.

    Construct from a precise date_of_birth (preferred) or a numeric age.
    Never construct from a frontend-provided "age band" string for security decisions.

    Example::

        policy = AgePolicy.from_dob(user_profile.date_of_birth)
        if not policy.is_health_hub_allowed():
            raise HTTPException(403, "Health Hub requires users to be 14 or older.")
    """

    def __init__(self, *, age: int | None = None) -> None:
        self._age = age

    @classmethod
    def from_dob(cls, dob: date) -> "AgePolicy":
        """Construct from a date_of_birth — the preferred, secure method."""
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return cls(age=age)

    @classmethod
    def from_age_int(cls, age: int) -> "AgePolicy":
        """Construct from a numeric age (use only when DOB is unavailable)."""
        return cls(age=age)

    # -- Primary gates -------------------------------------------------------

    def is_health_hub_allowed(self) -> bool:
        """Health Hub is available for users aged 14 and older."""
        if self._age is None:
            return False  # deny by default if age is unknown
        return self._age >= HEALTH_HUB_MIN_AGE

    def is_teen_mode(self) -> bool:
        """Returns True if user is in Teen Wellness Mode (14–17)."""
        if self._age is None:
            return False
        return TEEN_AGE_MIN <= self._age <= TEEN_AGE_MAX

    def is_adult_mode(self) -> bool:
        """Returns True if user is in Adult Wellness Mode (18+)."""
        if self._age is None:
            return False
        return self._age >= ADULT_AGE_MIN

    @property
    def age_band(self) -> str:
        """Human-readable band: 'teen', 'adult', or 'underage'."""
        if self._age is None:
            return "unknown"
        if self._age < HEALTH_HUB_MIN_AGE:
            return "underage"
        if self.is_teen_mode():
            return "teen"
        return "adult"

    # -- Backwards-compat properties -----------------------------------------

    @property
    def is_teen(self) -> bool:
        return self.is_teen_mode()

    @property
    def is_adult(self) -> bool:
        return self.is_adult_mode()

    # -- Feature gates -------------------------------------------------------

    def can_use_cycle_tracking(self) -> bool:
        """Users 14+ may use cycle tracking."""
        if self._age is None:
            return False
        return self._age >= TEEN_AGE_MIN

    def can_use_nutrition_tracking(self) -> bool:
        """Users 14+ may use nutrition tracking."""
        if self._age is None:
            return False
        return self._age >= TEEN_AGE_MIN

    def can_use_weight_features(self) -> bool:
        """Weight tracking is adult-only (18+)."""
        return self.is_adult_mode()

    def can_use_calorie_deficit_features(self) -> bool:
        """Calorie deficit / restrictive diet features are adult-only."""
        return self.is_adult_mode()

    def can_use_advanced_health_features(self) -> bool:
        """Advanced features (ovulation, fertility window, etc.) are adult-only."""
        return self.is_adult_mode()

    def can_use_ai_health_personalization(self) -> bool:
        """AI health context requires adult mode AND explicit user consent.
        Consent is stored in the HealthProfile; this gate checks only age eligibility.
        """
        return self.is_adult_mode()
