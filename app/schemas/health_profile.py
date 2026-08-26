"""Pydantic schemas for the Health Profile domain.

Request schemas validate incoming data.
Response schemas control what is returned to the client.
SQLAlchemy models are NEVER returned directly.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations — these are the authoritative backend codes.
# Frontend uses localized labels; backend uses these stable strings.
# ---------------------------------------------------------------------------


class ActivityLevel(StrEnum):
    SEDENTARY = "SEDENTARY"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    ACTIVE = "ACTIVE"
    VERY_ACTIVE = "VERY_ACTIVE"


class DietType(StrEnum):
    VEGETARIAN = "VEGETARIAN"
    NON_VEGETARIAN = "NON_VEGETARIAN"
    VEGAN = "VEGAN"
    EGGETARIAN = "EGGETARIAN"
    OTHER = "OTHER"


class ConditionCode(StrEnum):
    PCOS_PCOD = "PCOS_PCOD"
    ENDOMETRIOSIS = "ENDOMETRIOSIS"
    HYPOTHYROID = "HYPOTHYROID"
    HYPERTHYROID = "HYPERTHYROID"
    DIABETES = "DIABETES"
    ANEMIA = "ANEMIA"
    MIGRAINE = "MIGRAINE"
    OTHER = "OTHER"


class ConditionStatus(StrEnum):
    SELF_REPORTED = "self_reported"
    CLINICIAN_REPORTED = "clinician_reported"
    RESOLVED = "resolved"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Health Profile schemas
# ---------------------------------------------------------------------------


class HealthProfileCreate(BaseModel):
    """Schema for creating a new health profile (POST /api/v1/health-profile)."""

    date_of_birth: date = Field(..., description="User's date of birth")
    biological_sex: str | None = Field(
        default=None, description="MALE or FEMALE for calorie calculations"
    )
    height_cm: float | None = Field(
        default=None, ge=50.0, le=300.0, description="Height in centimetres"
    )
    weight_kg: float | None = Field(
        default=None, ge=10.0, le=500.0, description="Weight in kilograms"
    )
    activity_level: ActivityLevel = Field(
        default=ActivityLevel.SEDENTARY, description="Self-reported activity level"
    )
    diet_type: DietType = Field(
        default=DietType.OTHER, description="Primary diet type"
    )
    food_allergies: list[str] = Field(default_factory=list, max_length=20)
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=20)
    cycle_tracking_enabled: bool = Field(default=True)
    nutrition_tracking_enabled: bool = Field(default=True)
    activity_tracking_enabled: bool = Field(default=True)
    # AI personalization: explicitly must be set by the user, not defaulted to True.
    ai_health_personalization_enabled: bool = Field(default=False)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        from datetime import date as date_class
        today = date_class.today()
        if v >= today:
            raise ValueError("Date of birth must be in the past.")
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 14:
            raise ValueError(
                "Sakhi Health Hub is available for users aged 14 and older."
            )
        if age > 120:
            raise ValueError("Please enter a valid date of birth.")
        return v

    @field_validator("food_allergies", "dietary_restrictions", mode="before")
    @classmethod
    def sanitize_string_list(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(item).strip()[:100] for item in v if str(item).strip()]


class HealthProfileUpdate(BaseModel):
    """Schema for partial updates (PATCH /api/v1/health-profile).
    All fields are optional.
    """

    height_cm: float | None = Field(default=None, ge=50.0, le=300.0)
    biological_sex: str | None = None
    weight_kg: float | None = Field(default=None, ge=10.0, le=500.0)
    activity_level: ActivityLevel | None = None
    diet_type: DietType | None = None
    food_allergies: list[str] | None = None
    dietary_restrictions: list[str] | None = None
    cycle_tracking_enabled: bool | None = None
    nutrition_tracking_enabled: bool | None = None
    activity_tracking_enabled: bool | None = None
    ai_health_personalization_enabled: bool | None = None


class HealthProfileResponse(BaseModel):
    """Response schema — safe to serialise and send to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    date_of_birth: date
    biological_sex: str | None
    height_cm: float | None
    weight_kg: float | None
    activity_level: str
    diet_type: str
    food_allergies: list[str]
    dietary_restrictions: list[str]
    cycle_tracking_enabled: bool
    nutrition_tracking_enabled: bool
    activity_tracking_enabled: bool
    ai_health_personalization_enabled: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields derived server-side — never from client
    age_band: str = ""        # "teen" | "adult"
    is_health_hub_allowed: bool = True


# ---------------------------------------------------------------------------
# Permissions schemas (for GET/PATCH /api/v1/health-profile/permissions)
# ---------------------------------------------------------------------------


class HealthPermissionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycle_tracking_enabled: bool
    nutrition_tracking_enabled: bool
    activity_tracking_enabled: bool
    ai_health_personalization_enabled: bool


class HealthPermissionsUpdate(BaseModel):
    cycle_tracking_enabled: bool | None = None
    nutrition_tracking_enabled: bool | None = None
    activity_tracking_enabled: bool | None = None
    ai_health_personalization_enabled: bool | None = None


# ---------------------------------------------------------------------------
# Health Conditions schemas
# ---------------------------------------------------------------------------


class HealthConditionCreate(BaseModel):
    """Schema for adding a self-reported health condition."""

    condition_code: ConditionCode
    display_name: str = Field(min_length=2, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class HealthConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    condition_code: str
    display_name: str
    status: str
    reported_at: datetime
    created_at: datetime
