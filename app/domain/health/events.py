"""Canonical health event schema — Pydantic contract.

This is the **API-level** schema for health events, separate from the
SQLAlchemy ORM model in ``app/models/health.py``.  All external data
sources (wearables, manual entry, AI) MUST map their data into this
schema before it enters the Sakhi health domain.

Phase 0: Schema definition only — no endpoints consume it yet.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthEventSchema(BaseModel):
    """Canonical health event — source-agnostic representation.

    This schema is the single contract that all health data providers
    must produce.  Provider-specific fields are flattened into
    ``metadata`` so that no provider-specific schemas leak into the
    rest of the application.
    """

    id: str = Field(..., description="Unique event identifier")
    user_id: str = Field(..., description="Owning user ID")
    source: str = Field(..., description="Event source (e.g. 'manual', 'health_connect')")
    event_type: str = Field(..., description="Event type (e.g. 'steps', 'cycle')")
    start_time: datetime = Field(..., description="Event start time (UTC)")
    end_time: datetime | None = Field(default=None, description="Event end time (UTC)")
    value: float | None = Field(default=None, description="Numeric value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Provider-specific or additional context (never logged).",
    )
    source_event_id: str | None = Field(
        default=None,
        description="Original event ID from the data source",
    )
    created_at: datetime | None = Field(
        default=None, description="When this event was recorded in Sakhi"
    )

    model_config = {"from_attributes": True}
