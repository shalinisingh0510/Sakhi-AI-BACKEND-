"""Health domain ORM models — architectural contract only.

This module defines the **canonical HealthEvent** model that all future
health data (manual entries, wearable syncs, AI-generated insights)
must map into.  The table is intentionally *not* created in Phase 0;
it serves as the architectural contract for Phase 1+.

When ready to activate:
1.  Uncomment the model class.
2.  Import it in ``app/models/__init__.py``.
3.  Run ``alembic revision --autogenerate -m "add health_events table"``
4.  Run ``alembic upgrade head``
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# The model below is the ARCHITECTURAL CONTRACT for the canonical health
# event.  It will be uncommented in Phase 1 when health tables are created.
# ---------------------------------------------------------------------------

# from datetime import datetime
# from typing import Optional
#
# from sqlalchemy import DateTime, Enum, Float, Index, String, Text, func
# from sqlalchemy.orm import Mapped, mapped_column
#
# from app.db.base import Base
#
#
# class HealthEvent(Base):
#     """Canonical health event — the single table that all health data
#     sources map into.
#
#     Sources: manual, health_connect, healthkit, samsung_health, wearable.
#     Event types: steps, sleep, exercise, water, weight, heart_rate,
#                  nutrition, calories_burned, cycle, symptoms, mood, energy.
#     """
#
#     __tablename__ = "health_events"
#
#     id: Mapped[str] = mapped_column(String(32), primary_key=True)
#     user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
#     source: Mapped[str] = mapped_column(String(30), nullable=False)
#     event_type: Mapped[str] = mapped_column(String(30), nullable=False)
#     start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
#     end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
#     value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
#     unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
#     metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     source_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), server_default=func.now(), nullable=False
#     )
#
#     __table_args__ = (
#         Index("ix_health_events_user_type", "user_id", "event_type"),
#         Index("ix_health_events_user_time", "user_id", "start_time"),
#     )
