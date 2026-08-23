"""Repository classes for the Health Profile domain.

Uses the Phase 0 BaseRepository for common CRUD operations.
Domain-specific queries are added as methods here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.health_profile import HealthCondition, HealthProfile
from app.repositories.base import BaseRepository


class HealthProfileRepository(BaseRepository[HealthProfile]):
    """Repository for health_profiles table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, HealthProfile)

    def get_by_user_id(self, user_id: str) -> HealthProfile | None:
        """Return the health profile for a given user, or None."""
        return (
            self._session.query(HealthProfile)
            .filter(HealthProfile.user_id == user_id)
            .first()
        )

    def user_has_profile(self, user_id: str) -> bool:
        """Return True if a profile exists for the user."""
        return self.get_by_user_id(user_id) is not None


class HealthConditionRepository(BaseRepository[HealthCondition]):
    """Repository for health_conditions table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, HealthCondition)

    def list_by_user_id(self, user_id: str) -> list[HealthCondition]:
        """Return all active conditions for a user."""
        return (
            self._session.query(HealthCondition)
            .filter(HealthCondition.user_id == user_id)
            .order_by(HealthCondition.reported_at.desc())
            .all()
        )

    def get_by_id_and_user(
        self, condition_id: str, user_id: str
    ) -> HealthCondition | None:
        """Return a condition only if it belongs to the given user."""
        return (
            self._session.query(HealthCondition)
            .filter(
                HealthCondition.id == condition_id,
                HealthCondition.user_id == user_id,
            )
            .first()
        )
