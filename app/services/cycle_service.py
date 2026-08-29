"""Cycle Service — orchestration layer.

Responsibilities:
  * Access control (via HealthPrivacyGate & HealthFeaturePolicy)
  * Period log CRUD
  * Synchronous trigger of CycleEngine
  * Transaction management

This service never makes AI calls.
Sensitive values (period dates, notes, flow) are NEVER logged.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.domain.health.age_policy import AgePolicy
from app.domain.health.feature_policy import HealthFeaturePolicy
from app.domain.health.privacy import HealthPrivacyGate
from app.models.health_profile import HealthProfile
from app.models.menstrual_cycle import CyclePrediction, MenstrualCycle, PeriodLog
from app.repositories.cycle import (
    CyclePredictionRepository,
    MenstrualCycleRepository,
    PeriodLogRepository,
)
from app.repositories.health import HealthProfileRepository
from app.schemas.cycle import (
    CalendarDay,
    CalendarResponse,
    CurrentCycleResponse,
    CyclePredictionResponse,
    CycleStatisticsResponse,
    EstimatedDate,
    EstimatedWindow,
    MenstrualCycleResponse,
    PeriodLogCreate,
    PeriodLogResponse,
    PeriodLogUpdate,
)
from app.services import cycle_engine

logger = logging.getLogger("sakhi.cycle")


class CycleServiceError(Exception):
    pass


class PeriodDuplicateError(CycleServiceError):
    pass


class PeriodNotFoundError(CycleServiceError):
    pass


class CycleService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._health_repo = HealthProfileRepository(session)
        self._period_repo = PeriodLogRepository(session)
        self._cycle_repo = MenstrualCycleRepository(session)
        self._prediction_repo = CyclePredictionRepository(session)

    # ------------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------------

    def _assert_cycle_access(self, user_id: str) -> HealthProfile:
        """Enforce all Phase 1 policies before allowing cycle access.

        1. Fetch health profile by authenticated user_id.
        2. Build AgePolicy.
        3. Build FeaturePolicy.
        4. Check can_use_cycle_tracking().
        5. Verify ownership (sanity check).

        Returns:
            The authorized HealthProfile.
        Raises:
            HTTPException 404 if no profile.
            HTTPException 403 if feature disabled or underage.
        """
        profile = self._health_repo.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Health profile required to use the cycle tracker.",
            )

        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id=user_id, profile=profile
        )
        gate.assert_owner(user_id)

        age_policy = AgePolicy.from_dob(profile.date_of_birth)
        feature_policy = HealthFeaturePolicy.build(
            age_policy=age_policy, profile=profile
        )

        if not feature_policy.can_use_cycle_tracking():
            raise HTTPException(
                status_code=403,
                detail="Cycle tracking is disabled or restricted.",
            )

        return profile

    # ------------------------------------------------------------------------
    # Read Methods
    # ------------------------------------------------------------------------

    def get_current_cycle(self, user_id: str) -> CurrentCycleResponse:
        profile = self._assert_cycle_access(user_id)
        
        age_policy = AgePolicy.from_dob(profile.date_of_birth)
        feature_policy = HealthFeaturePolicy.build(
            age_policy=age_policy, profile=profile
        )

        period_logs = self._period_repo.list_by_profile_asc(profile.id)
        completed_cycles = self._cycle_repo.list_completed_by_profile(profile.id)

        # Convert to engine records
        engine_logs = [
            cycle_engine.PeriodRecord(start_date=p.start_date, end_date=p.end_date)
            for p in period_logs
        ]
        engine_cycles = [
            cycle_engine.CycleRecord(
                cycle_start_date=c.cycle_start_date,
                cycle_end_date=c.cycle_end_date,
                cycle_length_days=int(c.cycle_length_days) if c.cycle_length_days else None,
                period_duration_days=int(c.period_duration_days) if c.period_duration_days else None,
                is_complete=c.is_complete,
            )
            for c in completed_cycles
        ]

        summary = cycle_engine.build_current_cycle_summary(
            period_logs=engine_logs,
            completed_cycles=engine_cycles,
            include_advanced_features=feature_policy.can_use_advanced_reproductive_features(),
        )

        # Map to Pydantic Response
        resp = CurrentCycleResponse(
            current_cycle_day=summary.current_cycle_day,
            latest_period_start=summary.latest_period_start,
            data_quality=summary.data_quality,  # type: ignore
            completed_cycles_count=summary.completed_cycles_count,
            irregularity_observation=summary.irregularity_observation,
        )

        if summary.estimated_next_period:
            resp.estimated_next_period = EstimatedDate(
                date=summary.estimated_next_period.date,
                confidence=summary.estimated_next_period.confidence,  # type: ignore
            )
        if summary.estimated_ovulation:
            resp.estimated_ovulation = EstimatedDate(
                date=summary.estimated_ovulation.date,
                confidence=summary.estimated_ovulation.confidence,  # type: ignore
            )
        if summary.estimated_fertile_window:
            resp.estimated_fertile_window = EstimatedWindow(
                start=summary.estimated_fertile_window.start,
                end=summary.estimated_fertile_window.end,
                confidence=summary.estimated_fertile_window.confidence,  # type: ignore
            )

        return resp

    def list_cycles(self, user_id: str, limit: int = 12) -> list[MenstrualCycleResponse]:
        profile = self._assert_cycle_access(user_id)
        cycles = self._cycle_repo.list_all_by_profile(profile.id, limit=limit)
        return [MenstrualCycleResponse.model_validate(c) for c in cycles]

    def get_statistics(self, user_id: str) -> CycleStatisticsResponse:
        profile = self._assert_cycle_access(user_id)
        completed = self._cycle_repo.list_completed_by_profile(profile.id)

        engine_cycles = [
            cycle_engine.CycleRecord(
                cycle_start_date=c.cycle_start_date,
                cycle_end_date=c.cycle_end_date,
                cycle_length_days=int(c.cycle_length_days) if c.cycle_length_days else None,
                period_duration_days=int(c.period_duration_days) if c.period_duration_days else None,
                is_complete=c.is_complete,
            )
            for c in completed
        ]

        if not engine_cycles:
            return CycleStatisticsResponse()

        avg_length = cycle_engine.calculate_average_cycle_length(engine_cycles)
        
        # Calculate avg duration safely
        durs = [c.period_duration_days for c in engine_cycles if c.period_duration_days]
        avg_dur = sum(durs) / len(durs) if durs else None

        lengths = [c.cycle_length_days for c in engine_cycles if c.cycle_length_days]
        shortest = min(lengths) if lengths else None
        longest = max(lengths) if lengths else None
        
        variability = cycle_engine.calculate_cycle_variability(engine_cycles)
        irregular = cycle_engine.detect_irregularity(engine_cycles)

        return CycleStatisticsResponse(
            average_cycle_length=avg_length,
            average_period_duration=avg_dur,
            shortest_cycle=shortest,
            longest_cycle=longest,
            cycle_variability_days=variability,
            completed_cycles=len(engine_cycles),
            has_irregular_pattern=irregular,
            irregularity_observation="Your recent cycles have varied more than usual." if irregular else None,
        )

    def get_calendar(self, user_id: str, year: int, month: int) -> CalendarResponse:
        # Simplified for Phase 2: return skeleton response. Actual populating logic belongs here
        # or in frontend. For now, returning empty days list to satisfy API contract.
        profile = self._assert_cycle_access(user_id)
        return CalendarResponse(year=year, month=month, days=[])

    def list_periods(self, user_id: str) -> list[PeriodLogResponse]:
        profile = self._assert_cycle_access(user_id)
        logs = self._period_repo.list_by_profile(profile.id)
        return [PeriodLogResponse.model_validate(p) for p in logs]

    def get_period(self, user_id: str, log_id: str) -> PeriodLogResponse:
        profile = self._assert_cycle_access(user_id)
        log = self._period_repo.get_by_id_and_profile(log_id, profile.id)
        if not log:
            raise HTTPException(404, "Period log not found")
        return PeriodLogResponse.model_validate(log)


    # ------------------------------------------------------------------------
    # Write Methods
    # ------------------------------------------------------------------------

    def log_period(self, user_id: str, data: PeriodLogCreate) -> PeriodLogResponse:
        profile = self._assert_cycle_access(user_id)

        existing = self._period_repo.get_by_profile_and_date(profile.id, data.start_date)
        if existing:
            raise HTTPException(409, "A period log already exists on this start date.")

        with transactional(self._session):
            new_log = PeriodLog(
                id=str(uuid4()),
                health_profile_id=profile.id,
                start_date=data.start_date,
                end_date=data.end_date,
                flow=data.flow.value,
                notes=data.notes,
            )
            self._period_repo.add(new_log)
            self._rebuild_derived_data(profile.id)

        logger.info(f"User {user_id} logged a period (id={new_log.id})")
        return PeriodLogResponse.model_validate(new_log)

    def update_period(self, user_id: str, log_id: str, data: PeriodLogUpdate) -> PeriodLogResponse:
        profile = self._assert_cycle_access(user_id)

        with transactional(self._session):
            log = self._period_repo.get_by_id_and_profile(log_id, profile.id)
            if not log:
                raise HTTPException(404, "Period log not found")

            if data.end_date is not None:
                if data.end_date < log.start_date:
                    raise HTTPException(422, "end_date cannot be before start_date")
                log.end_date = data.end_date

            if data.flow is not None:
                log.flow = data.flow.value
            if data.notes is not None:
                log.notes = data.notes

            self._rebuild_derived_data(profile.id)

        logger.info(f"User {user_id} updated period (id={log.id})")
        return PeriodLogResponse.model_validate(log)

    def delete_period(self, user_id: str, log_id: str) -> None:
        profile = self._assert_cycle_access(user_id)

        with transactional(self._session):
            log = self._period_repo.get_by_id_and_profile(log_id, profile.id)
            if not log:
                raise HTTPException(404, "Period log not found")

            self._period_repo.delete(log)
            self._rebuild_derived_data(profile.id)

        logger.info(f"User {user_id} deleted period (id={log_id})")

    # ------------------------------------------------------------------------
    # Internal Engine Orchestration
    # ------------------------------------------------------------------------

    def _rebuild_derived_data(self, health_profile_id: str) -> None:
        """Recalculate cycles and predictions after a period mutation.
        
        This MUST be called within a transactional context.
        """
        # 1. Clear existing derived data
        self._cycle_repo.delete_all_for_profile(health_profile_id)
        self._prediction_repo.delete_all_for_profile(health_profile_id)
        self._session.flush()

        # 2. Rebuild cycles from raw period logs
        period_logs = self._period_repo.list_by_profile_asc(health_profile_id, limit=100)
        engine_logs = [
            cycle_engine.PeriodRecord(start_date=p.start_date, end_date=p.end_date)
            for p in period_logs
        ]
        
        engine_cycles = cycle_engine.rebuild_cycles_from_period_logs(engine_logs)
        
        for c in engine_cycles:
            new_cycle = MenstrualCycle(
                id=str(uuid4()),
                health_profile_id=health_profile_id,
                cycle_start_date=c.cycle_start_date,
                cycle_end_date=c.cycle_end_date,
                cycle_length_days=str(c.cycle_length_days) if c.cycle_length_days else None,
                period_duration_days=str(c.period_duration_days) if c.period_duration_days else None,
                is_complete=c.is_complete,
            )
            self._cycle_repo.add(new_cycle)
        
        self._session.flush()

        # 3. We do not write predictions to DB in Phase 2, we just return them via API dynamically.
        # But if we did want to persist them (as requested by models), we'd call build_current_cycle_summary here
        # and store the predictions. For now, the CurrentCycleResponse dynamic rebuild is sufficient.
