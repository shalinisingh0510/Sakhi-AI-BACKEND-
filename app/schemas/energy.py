"""Pydantic schemas for the Energy Overview domain."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityDailySummary


class CalculationStatus:
    SUCCESS = "SUCCESS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    TEEN_RESTRICTED = "TEEN_RESTRICTED"


class EnergySummaryResponse(BaseModel):
    """Response schema for a daily energy overview."""

    target_date: date
    
    # Intake (from NutritionEngine)
    calories_consumed: float
    
    # Expenditure (from EnergyExpenditureService + ActivityService)
    estimated_bmr: float | None = Field(
        default=None, description="Basal Metabolic Rate, None if insufficient data or restricted"
    )
    activity_calories_burned: float = Field(
        default=0.0, description="Calories burned from logged activities"
    )
    total_estimated_expenditure: float | None = Field(
        default=None, description="BMR + Activity, None if insufficient data or restricted"
    )
    
    # Balance
    energy_balance: float | None = Field(
        default=None, description="Consumed - Expended, None if insufficient data or restricted"
    )
    
    # Status
    calculation_status: str = Field(
        default=CalculationStatus.SUCCESS, 
        description="SUCCESS, INSUFFICIENT_DATA, or TEEN_RESTRICTED"
    )

    # Detailed summaries
    activity_summary: ActivityDailySummary
