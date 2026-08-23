"""Health data privacy gate — access control boundary.

Ensures that:
1. Health data is NEVER exposed to the AI layer without explicit
   user permission.
2. Health data is NEVER returned for a user other than the
   authenticated owner.
3. Sensitive health details are NEVER written to logs.

Phase 0: Interface only — concrete enforcement will be added in
Phase 1 alongside actual health endpoints.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("sakhi.health.privacy")


class HealthPrivacyGate:
    """Boundary enforcing health data access rules.

    All health service methods should call these checks before
    returning or processing health data.

    Example::

        gate = HealthPrivacyGate(authenticated_user_id="u123")
        gate.assert_owner(record.user_id)  # raises if mismatch
        if gate.ai_health_access_permitted():
            # build health context for AI
    """

    def __init__(self, *, authenticated_user_id: str) -> None:
        self._user_id = authenticated_user_id
        # Future: load user's privacy preferences from DB
        self._health_tracking_enabled: bool = True
        self._ai_health_access_enabled: bool = False  # default: opt-out

    def assert_owner(self, record_user_id: str) -> None:
        """Raise if the authenticated user does not own the record."""
        if record_user_id != self._user_id:
            logger.warning(
                "Health data ownership violation: authenticated_user=%s attempted_record_owner=%s",
                self._user_id,
                record_user_id,
            )
            raise PermissionError("You do not have permission to access this health record.")

    def health_tracking_permitted(self) -> bool:
        """Whether the user has health tracking enabled."""
        return self._health_tracking_enabled

    def ai_health_access_permitted(self) -> bool:
        """Whether the user permits health data to be sent to AI."""
        return self._ai_health_access_enabled

    def wearable_access_permitted(self) -> bool:
        """Whether the user permits wearable integrations."""
        # Future: check user preferences
        return False
