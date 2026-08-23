"""Repository classes for Wellness tracking."""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.symptom_log import SymptomLog
from app.models.mood_log import MoodLog
from app.models.energy_log import EnergyLog
from app.repositories.base import BaseRepository

class SymptomLogRepository(BaseRepository[SymptomLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SymptomLog)

    def list_by_profile(
        self,
        health_profile_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[SymptomLog]:
        """Return symptom logs, newest first, paginated."""
        return (
            self._session.query(SymptomLog)
            .filter(SymptomLog.health_profile_id == health_profile_id)
            .order_by(SymptomLog.start_date.desc(), SymptomLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
    def list_by_profile_and_date(
        self, health_profile_id: str, log_date: date
    ) -> Sequence[SymptomLog]:
        return (
            self._session.query(SymptomLog)
            .filter(
                SymptomLog.health_profile_id == health_profile_id,
                SymptomLog.start_date == log_date,
            )
            .order_by(SymptomLog.created_at.asc())
            .all()
        )

    def get_by_id_and_profile(
        self, log_id: str, health_profile_id: str
    ) -> SymptomLog | None:
        return (
            self._session.query(SymptomLog)
            .filter(
                SymptomLog.id == log_id,
                SymptomLog.health_profile_id == health_profile_id,
            )
            .first()
        )

class MoodLogRepository(BaseRepository[MoodLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MoodLog)
        
    def get_by_profile_and_date(
        self, health_profile_id: str, log_date: date
    ) -> MoodLog | None:
        return (
            self._session.query(MoodLog)
            .filter(
                MoodLog.health_profile_id == health_profile_id,
                MoodLog.log_date == log_date,
            )
            .first()
        )

    def list_by_profile(
        self, health_profile_id: str, limit: int = 30
    ) -> Sequence[MoodLog]:
        return (
            self._session.query(MoodLog)
            .filter(MoodLog.health_profile_id == health_profile_id)
            .order_by(MoodLog.log_date.desc())
            .limit(limit)
            .all()
        )

    def get_by_id_and_profile(
        self, log_id: str, health_profile_id: str
    ) -> MoodLog | None:
        return (
            self._session.query(MoodLog)
            .filter(
                MoodLog.id == log_id,
                MoodLog.health_profile_id == health_profile_id,
            )
            .first()
        )


class EnergyLogRepository(BaseRepository[EnergyLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, EnergyLog)
        
    def get_by_profile_and_date(
        self, health_profile_id: str, log_date: date
    ) -> EnergyLog | None:
        return (
            self._session.query(EnergyLog)
            .filter(
                EnergyLog.health_profile_id == health_profile_id,
                EnergyLog.log_date == log_date,
            )
            .first()
        )

    def list_by_profile(
        self, health_profile_id: str, limit: int = 30
    ) -> Sequence[EnergyLog]:
        return (
            self._session.query(EnergyLog)
            .filter(EnergyLog.health_profile_id == health_profile_id)
            .order_by(EnergyLog.log_date.desc())
            .limit(limit)
            .all()
        )

    def get_by_id_and_profile(
        self, log_id: str, health_profile_id: str
    ) -> EnergyLog | None:
        return (
            self._session.query(EnergyLog)
            .filter(
                EnergyLog.id == log_id,
                EnergyLog.health_profile_id == health_profile_id,
            )
            .first()
        )
