"""SQLAlchemy ORM models for the Health Profile domain.

Tables:
  health_profiles   — one per user, holds all wellness preferences.
  health_conditions — self-reported conditions (one-to-many with users).

Design notes:
  * These tables are managed by Alembic, NOT by _initialize_schema().
  * allergies + dietary_restrictions stored as JSON strings for flexibility.
  * ai_health_personalization_enabled defaults to False (explicit opt-in).
  * CASCADE on user deletion deliberately NOT set — account deletion must
    go through a deliberate data-purge workflow, not automatic cascade.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthProfile(Base):
    """Primary health profile for a Sakhi user.

    One profile per user (enforced by UNIQUE constraint on user_id).
    """

    __tablename__ = "health_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Age & body
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lifestyle
    activity_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SEDENTARY"
    )
    diet_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OTHER"
    )

    # Multi-value dietary data stored as JSON arrays.
    # e.g. '["gluten", "dairy"]'
    food_allergies_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_restrictions_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tracking preferences (default enabled, except AI which requires opt-in)
    cycle_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    nutrition_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    activity_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # IMPORTANT: AI health personalization is opt-in only. Default = False.
    ai_health_personalization_enabled: Mapped[bool] = mapped_column(
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
        UniqueConstraint("user_id", name="uq_health_profiles_user_id"),
        Index("ix_health_profiles_user_id", "user_id"),
    )

    # -- Helper properties for JSON fields -----------------------------------

    @property
    def food_allergies(self) -> list[str]:
        if not self.food_allergies_json:
            return []
        try:
            return json.loads(self.food_allergies_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @food_allergies.setter
    def food_allergies(self, value: list[str]) -> None:
        self.food_allergies_json = json.dumps(value or [])

    @property
    def dietary_restrictions(self) -> list[str]:
        if not self.dietary_restrictions_json:
            return []
        try:
            return json.loads(self.dietary_restrictions_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @dietary_restrictions.setter
    def dietary_restrictions(self, value: list[str]) -> None:
        self.dietary_restrictions_json = json.dumps(value or [])


class HealthCondition(Base):
    """Self-reported health condition for a user.

    IMPORTANT: These are self-reported only.  The AI must NEVER treat these
    as confirmed diagnoses.  The 'status' field captures the confidence level.
    """

    __tablename__ = "health_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Stable machine code (e.g. 'PCOS', 'HYPOTHYROID')
    condition_code: Mapped[str] = mapped_column(String(50), nullable=False)
    # Localised display name at time of recording
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Lifecycle status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="self_reported"
    )

    # Free-text notes — NEVER logged
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
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
        Index("ix_health_conditions_user_id", "user_id"),
        Index("ix_health_conditions_condition_code", "condition_code"),
    )
