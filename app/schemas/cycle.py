"""Pydantic schemas for the Menstrual Cycle domain.

All estimates are clearly labelled as estimates in the response objects.
No schema claims clinical certainty.

Response schemas are the authoritative API contract — SQLAlchemy models
are NEVER returned directly to clients.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FlowLevel(StrEnum):
    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"
    UNKNOWN = "UNKNOWN"


class PredictionType(StrEnum):
    NEXT_PERIOD = "NEXT_PERIOD"
    OVULATION = "OVULATION"
    FERTILE_WINDOW_START = "FERTILE_WINDOW_START"
    FERTILE_WINDOW_END = "FERTILE_WINDOW_END"


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DataQuality(StrEnum):
    """Qualitative description of available data for predictions."""
    NO_DATA = "NO_DATA"           # 0 periods logged
    INSUFFICIENT = "INSUFFICIENT"  # 1 period
    LIMITED = "LIMITED"            # 2 periods
    MODERATE = "MODERATE"          # 3–4 periods
    GOOD = "GOOD"                  # 5+ periods


# ---------------------------------------------------------------------------
# Period Log request/response schemas
# ---------------------------------------------------------------------------


class PeriodLogCreate(BaseModel):
    """Create a new period log entry.

    Only start_date is required — users may not know the end date yet.
    """

    start_date: date = Field(..., description="First day of the period (calendar date)")
    end_date: Optional[date] = Field(
        default=None, description="Last day of the period (optional)"
    )
    flow: FlowLevel = Field(
        default=FlowLevel.UNKNOWN, description="Flow intensity"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Optional free-text notes"
    )

    @field_validator("start_date")
    @classmethod
    def validate_start_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Period start date cannot be in the future.")
        return v

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_after_start(cls, v: Optional[date]) -> Optional[date]:
        return v  # Cross-field validation handled in model_validator below

    def model_post_init(self, __context: object) -> None:  # type: ignore[override]
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")


class PeriodLogUpdate(BaseModel):
    """Partial update for a period log."""

    end_date: Optional[date] = None
    flow: Optional[FlowLevel] = None
    notes: Optional[str] = Field(default=None, max_length=500)

    def model_post_init(self, __context: object) -> None:  # type: ignore[override]
        pass  # Cross-field validation done in service layer where start_date is available.


class PeriodLogResponse(BaseModel):
    """Safe response for a period log — sent to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    start_date: date
    end_date: Optional[date]
    flow: str
    notes: Optional[str]  # Included in response; NEVER logged server-side.
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Menstrual Cycle response
# ---------------------------------------------------------------------------


class MenstrualCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    health_profile_id: str
    cycle_start_date: date
    cycle_end_date: Optional[date]
    cycle_length_days: Optional[int]
    period_duration_days: Optional[int]
    is_complete: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Prediction sub-schemas
# ---------------------------------------------------------------------------


class EstimatedDate(BaseModel):
    """A single estimated date with associated confidence and metadata."""

    date: date
    confidence: ConfidenceLevel
    algorithm_version: str = "cycle-v1"


class EstimatedWindow(BaseModel):
    """An estimated date range (e.g. fertile window)."""

    start: date
    end: date
    confidence: ConfidenceLevel
    algorithm_version: str = "cycle-v1"


# ---------------------------------------------------------------------------
# Current cycle summary
# ---------------------------------------------------------------------------


class CurrentCycleResponse(BaseModel):
    """Aggregate response for the current cycle dashboard.

    All prediction fields are Optional — the frontend must handle missing data
    gracefully and show appropriate empty states.

    IMPORTANT: These are ESTIMATES. The frontend must display them as such.
    """

    current_cycle_day: Optional[int] = None
    latest_period_start: Optional[date] = None
    data_quality: DataQuality = DataQuality.NO_DATA
    completed_cycles_count: int = 0

    # ESTIMATES — clearly named as such in the schema
    estimated_next_period: Optional[EstimatedDate] = None
    # Ovulation/fertile window only populated for 18+ users (can_use_advanced_reproductive_features)
    estimated_ovulation: Optional[EstimatedDate] = None
    estimated_fertile_window: Optional[EstimatedWindow] = None

    # Irregularity observation (never a diagnosis)
    irregularity_observation: Optional[str] = None


# ---------------------------------------------------------------------------
# Cycle statistics
# ---------------------------------------------------------------------------


class CycleStatisticsResponse(BaseModel):
    average_cycle_length: Optional[float] = None
    average_period_duration: Optional[float] = None
    shortest_cycle: Optional[int] = None
    longest_cycle: Optional[int] = None
    cycle_variability_days: Optional[float] = None
    completed_cycles: int = 0
    has_irregular_pattern: bool = False
    irregularity_observation: Optional[str] = None


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


class CalendarDay(BaseModel):
    """A single day's state for the calendar UI."""

    date: date
    is_period_day: bool = False
    is_today: bool = False
    is_estimated_period: bool = False
    is_estimated_ovulation: bool = False
    is_estimated_fertile: bool = False
    flow: Optional[str] = None
    # ARIA label for accessibility
    aria_label: str = ""


class CalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDay]


# ---------------------------------------------------------------------------
# Prediction card response (used by PredictionCard.tsx)
# ---------------------------------------------------------------------------


class CyclePredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prediction_type: str
    predicted_start_date: date
    predicted_end_date: Optional[date]
    confidence: str
    algorithm_version: str
    calculated_at: datetime
