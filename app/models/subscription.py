"""SQLAlchemy ORM models for Subscriptions and Entitlements.

Tables:
  subscription_plans  — Define available tiers (Free, Pro, Premium).
  user_subscriptions  — Track user's active/past_due subscriptions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubscriptionPlan(Base):
    """Available subscription tiers."""

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., "plan_pro_monthly"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    interval: Mapped[str] = mapped_column(String(20), nullable=False, default="month")  # month, year, lifetime
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    from sqlalchemy import text
    # JSON list of features included in this plan
    features: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserSubscription(Base):
    """Tracks a user's subscription status and history."""

    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscription_plans.id"), nullable=False)
    
    # active, past_due, canceled, trialing
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")  # razorpay, stripe, mock
    provider_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        Index("ix_user_subscriptions_user_id", "user_id"),
        Index("ix_user_subscriptions_provider_sub_id", "provider_subscription_id"),
    )
