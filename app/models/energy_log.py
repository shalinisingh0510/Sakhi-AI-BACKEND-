"""SQLAlchemy ORM models for Energy Tracking.

energy_logs:
  Records daily energy states.
"""
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, String, Text, Index, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class EnergyLog(Base):
    __tablename__ = "energy_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    energy_level: Mapped[str] = mapped_column(String(50), nullable=False)
    
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cycle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
        UniqueConstraint("health_profile_id", "log_date", name="uq_energy_logs_profile_date"),
        Index("ix_energy_logs_health_profile_id", "health_profile_id"),
        Index("ix_energy_logs_log_date", "log_date"),
        Index("ix_energy_logs_cycle_id", "cycle_id"),
    )
