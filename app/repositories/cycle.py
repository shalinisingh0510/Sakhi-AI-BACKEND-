"""Repository classes for the Menstrual Cycle domain.

All queries are health_profile_id-scoped — never user_id directly.
The calling service layer is responsible for verifying that the
health_profile belongs to the authenticated user (via HealthPrivacyGate).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.menstrual_cycle import CyclePrediction, MenstrualCycle, PeriodLog
from app.repositories.base import BaseRepository


class PeriodLogRepository(BaseRepository[PeriodLog]):
    """Repository for period_logs table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PeriodLog)

    def get_latest_by_profile(self, health_profile_id: str) -> PeriodLog | None:
        """Return the most recent period log for a profile."""
        return (
            self._session.query(PeriodLog)
            .filter(PeriodLog.health_profile_id == health_profile_id)
            .order_by(PeriodLog.start_date.desc())
            .first()
        )

    def list_by_profile(
        self,
        health_profile_id: str,
        limit: int = 24,
    ) -> list[PeriodLog]:
        """Return recent period logs, newest first."""
        return (
            self._session.query(PeriodLog)
            .filter(PeriodLog.health_profile_id == health_profile_id)
            .order_by(PeriodLog.start_date.desc())
            .limit(limit)
            .all()
        )

    def list_by_profile_asc(
        self,
        health_profile_id: str,
        limit: int = 24,
    ) -> list[PeriodLog]:
        """Return period logs sorted ascending (oldest first) — used by cycle engine."""
        return (
            self._session.query(PeriodLog)
            .filter(PeriodLog.health_profile_id == health_profile_id)
            .order_by(PeriodLog.start_date.asc())
            .limit(limit)
            .all()
        )

    def get_by_profile_and_date(
        self, health_profile_id: str, start_date: date
    ) -> PeriodLog | None:
        """Check for duplicate (health_profile_id, start_date) before insert."""
        return (
            self._session.query(PeriodLog)
            .filter(
                PeriodLog.health_profile_id == health_profile_id,
                PeriodLog.start_date == start_date,
            )
            .first()
        )

    def get_by_id_and_profile(
        self, log_id: str, health_profile_id: str
    ) -> PeriodLog | None:
        """Ownership-scoped lookup — returns None if log belongs to another profile."""
        return (
            self._session.query(PeriodLog)
            .filter(
                PeriodLog.id == log_id,
                PeriodLog.health_profile_id == health_profile_id,
            )
            .first()
        )


class MenstrualCycleRepository(BaseRepository[MenstrualCycle]):
    """Repository for menstrual_cycles table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, MenstrualCycle)

    def list_completed_by_profile(
        self, health_profile_id: str, limit: int = 12
    ) -> list[MenstrualCycle]:
        """Return completed cycles, newest first."""
        return (
            self._session.query(MenstrualCycle)
            .filter(
                MenstrualCycle.health_profile_id == health_profile_id,
                MenstrualCycle.is_complete.is_(True),
            )
            .order_by(MenstrualCycle.cycle_start_date.desc())
            .limit(limit)
            .all()
        )

    def list_all_by_profile(
        self, health_profile_id: str, limit: int = 12
    ) -> list[MenstrualCycle]:
        """Return all cycles (including current incomplete), newest first."""
        return (
            self._session.query(MenstrualCycle)
            .filter(MenstrualCycle.health_profile_id == health_profile_id)
            .order_by(MenstrualCycle.cycle_start_date.desc())
            .limit(limit)
            .all()
        )

    def list_for_calendar(
        self,
        health_profile_id: str,
        from_date: date,
        to_date: date,
    ) -> list[MenstrualCycle]:
        """Return cycles whose start date falls within [from_date, to_date]."""
        return (
            self._session.query(MenstrualCycle)
            .filter(
                MenstrualCycle.health_profile_id == health_profile_id,
                MenstrualCycle.cycle_start_date >= from_date,
                MenstrualCycle.cycle_start_date <= to_date,
            )
            .order_by(MenstrualCycle.cycle_start_date.asc())
            .all()
        )

    def get_by_id_and_profile(
        self, cycle_id: str, health_profile_id: str
    ) -> MenstrualCycle | None:
        return (
            self._session.query(MenstrualCycle)
            .filter(
                MenstrualCycle.id == cycle_id,
                MenstrualCycle.health_profile_id == health_profile_id,
            )
            .first()
        )

    def delete_all_for_profile(self, health_profile_id: str) -> None:
        """Delete all cycle records for a profile (called before rebuild)."""
        self._session.query(MenstrualCycle).filter(
            MenstrualCycle.health_profile_id == health_profile_id
        ).delete(synchronize_session=False)


class CyclePredictionRepository(BaseRepository[CyclePrediction]):
    """Repository for cycle_predictions table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CyclePrediction)

    def get_latest_by_type(
        self, health_profile_id: str, prediction_type: str
    ) -> CyclePrediction | None:
        return (
            self._session.query(CyclePrediction)
            .filter(
                CyclePrediction.health_profile_id == health_profile_id,
                CyclePrediction.prediction_type == prediction_type,
            )
            .order_by(CyclePrediction.calculated_at.desc())
            .first()
        )

    def list_by_profile(
        self, health_profile_id: str
    ) -> list[CyclePrediction]:
        return (
            self._session.query(CyclePrediction)
            .filter(CyclePrediction.health_profile_id == health_profile_id)
            .order_by(CyclePrediction.prediction_type.asc())
            .all()
        )

    def delete_all_for_profile(self, health_profile_id: str) -> None:
        """Delete all predictions for a profile (called before rebuild)."""
        self._session.query(CyclePrediction).filter(
            CyclePrediction.health_profile_id == health_profile_id
        ).delete(synchronize_session=False)
