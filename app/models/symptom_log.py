"""SQLAlchemy ORM models for Symptom Tracking.

symptom_logs:
  Records individual symptom occurrences.
  Multiple symptoms can be logged per day.
  cycle_id and cycle_day are derived automatically by the CycleService,
  and may be NULL if the user does not have an active cycle.
"""
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, String, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("health_profiles.id", ondelete="CASCADE"), nullable=False)
    
    # Optional link to a specific menstrual cycle record.
    # We don't use a strict FK constraint to avoid CASCADE complexities if cycles are recalculated,
    # but logically it points to menstrual_cycles.id
    cycle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("menstrual_cycles.id", ondelete="SET NULL"), nullable=True)
    cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    symptom_code: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Free-text notes — NEVER logged in monitoring/telemetry
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
        Index("ix_symptom_logs_health_profile_id", "health_profile_id"),
        Index("ix_symptom_logs_start_date", "start_date"),
        Index("ix_symptom_logs_symptom_code", "symptom_code"),
        Index("ix_symptom_logs_cycle_id", "cycle_id"),
    )
