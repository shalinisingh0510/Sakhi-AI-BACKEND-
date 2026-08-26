"""Pydantic schemas for the Activity domain."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.activity import ActivityIntensity


class ActivityCreate(BaseModel):
    """Schema for logging a new activity."""

    activity_date: date = Field(..., description="Date the activity was performed")
    activity_type: str = Field(..., description="Type of activity (e.g. WALKING)")
    duration_minutes: int = Field(..., gt=0, le=1440, description="Duration in minutes")
    intensity: str = Field(
        default=ActivityIntensity.MODERATE, description="LOW, MODERATE, HIGH"
    )
    distance_km: float | None = Field(default=None, ge=0.0)
    steps: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)
    cycle_id: str | None = Field(default=None, description="Optional cycle association")


class ActivityUpdate(BaseModel):
    """Schema for updating an existing activity."""

    activity_type: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    intensity: str | None = None
    distance_km: float | None = Field(default=None, ge=0.0)
    steps: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class ActivityResponse(BaseModel):
    """Response schema for a logged activity."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    activity_date: date
    activity_type: str
    duration_minutes: int
    intensity: str
    distance_km: float | None
    steps: int | None
    estimated_calories_burned: float
    source: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ActivityDailySummary(BaseModel):
    """Summary of activities for a specific day."""
    
    activity_date: date
    total_duration_minutes: int
    total_estimated_calories_burned: float
    total_steps: int | None
    activities: list[ActivityResponse]
