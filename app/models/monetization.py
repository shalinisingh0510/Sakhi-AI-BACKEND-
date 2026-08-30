"""Monetization models for Sakhi AI.

Includes models for Phase 9 (Ads) and Phase 10 (Sponsorship & Affiliates).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Index, String, Text, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base

class AdPlacementConfig(Base):
    """Configuration for an Ad slot placement."""
    __tablename__ = "ad_placement_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    placement: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="ADSENSE")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    audience_policy: Mapped[str] = mapped_column(String(20), default="ALL", server_default="ALL")
    config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_ad_placement_configs_placement", "placement"),
    )

class Sponsor(Base):
    """Direct Sponsorship entities."""
    __tablename__ = "sponsors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_sponsors_status", "status"),
    )

class AffiliatePartner(Base):
    """Affiliate Partner Networks."""
    __tablename__ = "affiliate_partners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow
    )

    products: Mapped[list["AffiliateProduct"]] = relationship(
        "AffiliateProduct", back_populates="partner", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_affiliate_partners_status", "status"),
    )

class AffiliateProduct(Base):
    """Individual Affiliate Products."""
    __tablename__ = "affiliate_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    partner_id: Mapped[str] = mapped_column(String(36), ForeignKey("affiliate_partners.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    disclosure_text: Mapped[str | None] = mapped_column(String(255), default="Some links may earn Sakhi a commission.")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow
    )

    partner: Mapped["AffiliatePartner"] = relationship("AffiliatePartner", back_populates="products")

    __table_args__ = (
        Index("ix_affiliate_products_partner_id", "partner_id"),
        Index("ix_affiliate_products_status", "status"),
    )
