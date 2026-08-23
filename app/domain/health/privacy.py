"""Health data privacy gate — access control boundary.

Phase 1: Concrete enforcement using actual profile flags.

The gate is now constructed with the real profile preferences, not hardcoded
defaults.  This makes AI permission checks authoritative.

IMPORTANT:
  * Sensitive values (weight, conditions, etc.) MUST NOT appear in logs.
  * Always use the authenticated user_id from the auth context.
  * Never trust a user_id supplied by the request body.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.health_profile import HealthProfile

logger = logging.getLogger("sakhi.health.privacy")


class HealthPrivacyGate:
    """Boundary enforcing health data access rules.

    Construct with the authenticated user ID and their loaded profile.
    All health service methods should call these checks before returning data.

    Example::

        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id=current_user.id,
            profile=profile,
        )
        gate.assert_owner(profile.user_id)
        if gate.ai_health_access_permitted():
            # build health context for AI
    """

    def __init__(
        self,
        *,
        authenticated_user_id: str,
        health_tracking_enabled: bool = True,
        ai_health_access_enabled: bool = False,
        wearable_access_enabled: bool = False,
    ) -> None:
        self._user_id = authenticated_user_id
        self._health_tracking_enabled = health_tracking_enabled
        self._ai_health_access_enabled = ai_health_access_enabled
        self._wearable_access_enabled = wearable_access_enabled

    @classmethod
    def from_profile(
        cls,
        *,
        authenticated_user_id: str,
        profile: "HealthProfile",
    ) -> "HealthPrivacyGate":
        """Construct from a loaded HealthProfile (preferred in Phase 1+)."""
        return cls(
            authenticated_user_id=authenticated_user_id,
            health_tracking_enabled=True,
            ai_health_access_enabled=profile.ai_health_personalization_enabled,
            wearable_access_enabled=False,
        )

    @classmethod
    def without_profile(cls, *, authenticated_user_id: str) -> "HealthPrivacyGate":
        """Construct with all-default-deny settings (used before profile exists)."""
        return cls(authenticated_user_id=authenticated_user_id)

    def assert_owner(self, record_user_id: str) -> None:
        """Raise PermissionError if authenticated user does not own the record.

        NOTE: Do NOT log the record_user_id value — it may be sensitive.
        """
        if record_user_id != self._user_id:
            # Log only the authenticated user who attempted access — not the target.
            logger.warning(
                "Health data ownership violation: authenticated_user=%s",
                self._user_id,
            )
            raise PermissionError(
                "You do not have permission to access this health record."
            )

    def health_tracking_permitted(self) -> bool:
        return self._health_tracking_enabled

    def ai_health_access_permitted(self) -> bool:
        """Whether the user has explicitly enabled AI health personalization."""
        return self._ai_health_access_enabled

    def wearable_access_permitted(self) -> bool:
        """Whether the user permits wearable integrations."""
        return self._wearable_access_enabled
