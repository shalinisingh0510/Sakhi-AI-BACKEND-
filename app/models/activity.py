"""SQLAlchemy ORM models for the Activity and Energy domain (Phase 6/7).

Tables:
  activity_logs — one record per activity logged by the user.

Design notes:
  * duration_minutes is the primary input.
  * estimated_calories_burned is computed by the backend using METs.
  * No user-provided explicit calorie values unless explicitly overriding (MANUAL source).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivitySource:
    MANUAL = "MANUAL"
    ESTIMATED = "ESTIMATED"
    WEARABLE = "WEARABLE"
    IMPORTED = "IMPORTED"


class ActivityIntensity:
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class ActivityLog(Base):
    """A single logged activity for a user."""

    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("health_profiles.id", ondelete="CASCADE"), nullable=False
    )
    
    # Optional link to cycle for longitudinal analysis
    cycle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Core activity data
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ActivityIntensity.MODERATE
    )
    
    # Optional metrics
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Backend-calculated estimate
    estimated_calories_burned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Provenance
    source: Mapped[str] = mapped_column(String(30), nullable=False, default=ActivitySource.ESTIMATED)
    calculation_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    algorithm_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Wearable/Import metadata (for Phase 8+)
    external_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_record_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        Index("ix_activity_logs_health_profile_id", "health_profile_id"),
        Index("ix_activity_logs_date", "activity_date"),
        Index("ix_activity_logs_profile_date", "health_profile_id", "activity_date"),
        Index("ix_activity_logs_cycle_id", "cycle_id"),
    )
