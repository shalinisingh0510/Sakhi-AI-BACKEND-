"""SQLAlchemy ORM models for the Menstrual Cycle domain.

Tables:
  period_logs        — raw user-entered period start/end data (source of truth).
  menstrual_cycles   — derived cycle records (system-calculated from consecutive PeriodLogs).
  cycle_predictions  — calculated future estimates (NEXT_PERIOD, OVULATION, FERTILE_WINDOW).

Design principles:
  * Raw user data (period_logs) is ALWAYS kept separate from derived data.
  * Predictions are re-calculated synchronously after any period create/update/delete.
  * algorithm_version is stored on every prediction so historical accuracy can be traced.
  * Sensitive health data (dates, flow, notes) MUST NEVER appear in application logs.
  * CASCADE on user deletion deliberately NOT set — follow the data-purge policy.

Relationships:
  users → health_profiles → period_logs
  users → health_profiles → menstrual_cycles
  users → health_profiles → cycle_predictions
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PeriodLog(Base):
    """Raw user-entered period record.

    This is the source of truth.  All cycle calculations derive from these records.

    IMPORTANT:
      * end_date is optional — users may not know when their period ended.
      * notes field is free text and MUST NEVER be logged.
      * Duplicate (health_profile_id, start_date) is prevented by unique constraint.
    """

    __tablename__ = "period_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # User-entered dates — store as DATE only (not TIMESTAMPTZ).
    # A period start on "August 10" is a calendar date, not a UTC instant.
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Controlled vocabulary for flow intensity.
    # NEVER accept arbitrary strings from the client.
    flow: Mapped[str] = mapped_column(
        String(10), nullable=False, default="UNKNOWN"
    )

    # Free-text notes — NEVER logged.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "health_profile_id",
            "start_date",
            name="uq_period_logs_profile_start",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_period_logs_end_after_start",
        ),
        Index("ix_period_logs_health_profile_id", "health_profile_id"),
        Index("ix_period_logs_start_date", "start_date"),
    )


class MenstrualCycle(Base):
    """Derived cycle record — system-calculated from consecutive PeriodLogs.

    NEVER create these directly from the API. They are built by the cycle engine
    after period log mutations.

    cycle_length_days:
        Number of calendar days from the first day of THIS cycle (cycle_start_date)
        to the first day of the NEXT cycle.  NULL until the next period is logged.

    period_duration_days:
        (end_date - start_date).days + 1.  NULL if end_date is not recorded.

    is_complete:
        True when cycle_end_date is known (i.e. next period has started).
    """

    __tablename__ = "menstrual_cycles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Corresponds to the period_log.start_date of the period that began this cycle.
    cycle_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # The day before the next period started (i.e. last day of this cycle).
    # NULL until the next period is logged.
    cycle_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Derived integers — computed by cycle_engine.
    cycle_length_days: Mapped[int | None] = mapped_column(
        String(10), nullable=True
    )
    period_duration_days: Mapped[int | None] = mapped_column(
        String(10), nullable=True
    )

    is_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "health_profile_id",
            "cycle_start_date",
            name="uq_menstrual_cycles_profile_start",
        ),
        Index("ix_menstrual_cycles_health_profile_id", "health_profile_id"),
        Index("ix_menstrual_cycles_cycle_start_date", "cycle_start_date"),
    )


class CyclePrediction(Base):
    """Calculated future estimate for a single event type.

    IMPORTANT:
      * These are ESTIMATES, not facts.
      * Every prediction stores algorithm_version so future algorithm changes
        can be traced back to historical records.
      * Predictions are invalidated and rebuilt after every period mutation.
      * Do NOT send these values to any AI without the user's ai_health_personalization_enabled == True.

    prediction_type values:
      NEXT_PERIOD
      OVULATION
      FERTILE_WINDOW_START
      FERTILE_WINDOW_END
    """

    __tablename__ = "cycle_predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Optional back-reference to the cycle that anchored this prediction.
    reference_cycle_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )

    prediction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # LOW | MEDIUM | HIGH
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(80), nullable=False)

    # Version string — update this when the algorithm changes.
    algorithm_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="cycle-v1"
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_cycle_predictions_health_profile_id", "health_profile_id"),
        Index("ix_cycle_predictions_type", "prediction_type"),
        Index("ix_cycle_predictions_predicted_start", "predicted_start_date"),
    )
