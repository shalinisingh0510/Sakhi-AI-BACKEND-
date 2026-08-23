"""Pydantic schemas for Wellness Tracking (Symptoms, Mood, Energy).

These are daily observations, not medical diagnoses.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SymptomCategory(StrEnum):
    MENSTRUAL = "MENSTRUAL"
    PAIN = "PAIN"
    DIGESTIVE = "DIGESTIVE"
    GENERAL = "GENERAL"
    SKIN = "SKIN"
    HAIR = "HAIR"
    URINARY = "URINARY"
    REPRODUCTIVE = "REPRODUCTIVE"
    MOOD_RELATED = "MOOD_RELATED"
    OTHER = "OTHER"

class Severity(StrEnum):
    NONE = "NONE"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"

class MoodCode(StrEnum):
    HAPPY = "HAPPY"
    CALM = "CALM"
    NEUTRAL = "NEUTRAL"
    SAD = "SAD"
    IRRITATED = "IRRITATED"
    ANXIOUS = "ANXIOUS"
    STRESSED = "STRESSED"
    LOW = "LOW"
    ENERGETIC = "ENERGETIC"
    OTHER = "OTHER"

class MoodIntensity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class EnergyLevel(StrEnum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

# ---------------------------------------------------------------------------
# Symptom Schemas
# ---------------------------------------------------------------------------

class SymptomLogCreate(BaseModel):
    symptom_code: str = Field(..., max_length=50)
    category: SymptomCategory
    severity: Severity = Severity.MILD
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)

class SymptomLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    cycle_id: Optional[str]
    cycle_day: Optional[int]
    symptom_code: str
    category: str
    severity: str
    start_date: date
    end_date: Optional[date]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

# ---------------------------------------------------------------------------
# Mood Schemas
# ---------------------------------------------------------------------------

class MoodLogCreate(BaseModel):
    mood_code: MoodCode
    intensity: MoodIntensity = MoodIntensity.MEDIUM
    log_date: date
    notes: Optional[str] = Field(default=None, max_length=500)

class MoodLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    mood_code: str
    intensity: str
    log_date: date
    notes: Optional[str]
    cycle_id: Optional[str]
    cycle_day: Optional[int]
    created_at: datetime
    updated_at: datetime

# ---------------------------------------------------------------------------
# Energy Schemas
# ---------------------------------------------------------------------------

class EnergyLogCreate(BaseModel):
    energy_level: EnergyLevel
    log_date: date
    notes: Optional[str] = Field(default=None, max_length=500)

class EnergyLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    energy_level: str
    log_date: date
    notes: Optional[str]
    cycle_id: Optional[str]
    cycle_day: Optional[int]
    created_at: datetime
    updated_at: datetime

# ---------------------------------------------------------------------------
# Daily Check-In Schemas
# ---------------------------------------------------------------------------

class DailyCheckInCreate(BaseModel):
    """Payload for the daily check-in flow."""
    log_date: date
    mood: Optional[MoodLogCreate] = None
    energy: Optional[EnergyLogCreate] = None
    symptoms: list[SymptomLogCreate] = []

class DailyCheckInResponse(BaseModel):
    """Aggregate response for today's check-in."""
    log_date: date
    mood: Optional[MoodLogResponse] = None
    energy: Optional[EnergyLogResponse] = None
    symptoms: list[SymptomLogResponse] = []
