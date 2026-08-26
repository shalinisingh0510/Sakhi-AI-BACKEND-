"""Longitudinal Wellness API endpoints (Phase 8)."""

from __future__ import annotations

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.longitudinal import SymptomPattern, TrackingCompleteness, WellnessTrend
from app.services.auth import StoredUser
from app.services.longitudinal.data_service import LongitudinalDataService
from app.services.longitudinal.date_range import TimeRange, get_date_range
from app.services.longitudinal.pattern_engine import SymptomPatternEngine
from app.services.longitudinal.trend_engine import WellnessTrendEngine

router = APIRouter(tags=["wellness-longitudinal"])

class LongitudinalTrendsResponse(BaseModel):
    date_range: str
    trends: List[WellnessTrend]
    completeness: TrackingCompleteness

class LongitudinalPatternsResponse(BaseModel):
    date_range: str
    symptom_patterns: List[SymptomPattern]


@router.get(
    "/wellness/trends",
    response_model=LongitudinalTrendsResponse,
    summary="Get longitudinal wellness trends",
)
def get_wellness_trends(
    time_range: TimeRange = Query("30d", description="Time range for trends (e.g., 7d, 30d, 90d)"),
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LongitudinalTrendsResponse:
    
    data_service = LongitudinalDataService(db)
    target_date = date.today()
    start_date, end_date = get_date_range(target_date, time_range)
    
    # Previous period for comparison
    days_in_range = (end_date - start_date).days
    prev_end_date = start_date - type(end_date - start_date)(days=1)
    prev_start_date = prev_end_date - type(end_date - start_date)(days=days_in_range)
    
    # Get current period data
    curr_energy = data_service.get_energy_history(current_user.id, start_date, end_date)
    curr_activity = data_service.get_activity_history(current_user.id, start_date, end_date)
    curr_mood = data_service.get_mood_history(current_user.id, start_date, end_date)
    curr_symptoms = data_service.get_symptom_history(current_user.id, start_date, end_date)
    curr_nutrition = data_service.get_nutrition_history(current_user.id, start_date, end_date)
    
    # Get previous period data
    prev_energy = data_service.get_energy_history(current_user.id, prev_start_date, prev_end_date)
    prev_activity = data_service.get_activity_history(current_user.id, prev_start_date, prev_end_date)
    
    trends = [
        WellnessTrendEngine.analyze_energy_trend(curr_energy, prev_energy),
        WellnessTrendEngine.analyze_activity_trend(curr_activity, prev_activity)
    ]
    
    completeness = WellnessTrendEngine.calculate_completeness(
        days=days_in_range,
        energy_count=len(curr_energy),
        mood_count=len(curr_mood),
        symptom_count=len(curr_symptoms),
        activity_count=len(curr_activity),
        nutrition_count=len(curr_nutrition)
    )
    
    return LongitudinalTrendsResponse(
        date_range=f"{start_date.isoformat()} to {end_date.isoformat()}",
        trends=trends,
        completeness=completeness
    )


@router.get(
    "/wellness/patterns",
    response_model=LongitudinalPatternsResponse,
    summary="Get longitudinal wellness patterns",
)
def get_wellness_patterns(
    time_range: TimeRange = Query("90d", description="Time range for patterns (e.g., 30d, 90d, 6mo)"),
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LongitudinalPatternsResponse:
    
    data_service = LongitudinalDataService(db)
    target_date = date.today()
    start_date, end_date = get_date_range(target_date, time_range)
    
    symptoms = data_service.get_symptom_history(current_user.id, start_date, end_date)
    cycle_logs = data_service.get_cycle_history(current_user.id, start_date, end_date)
    
    frequent = SymptomPatternEngine.find_frequent_symptoms(symptoms)
    correlated = SymptomPatternEngine.find_cycle_correlations(symptoms, cycle_logs)
    
    # Merge them or just return correlated if preferred. Let's return correlated + anything frequent not in correlated
    correlated_codes = {p.symptom_code for p in correlated}
    combined = correlated + [f for f in frequent if f.symptom_code not in correlated_codes]
    
    return LongitudinalPatternsResponse(
        date_range=f"{start_date.isoformat()} to {end_date.isoformat()}",
        symptom_patterns=combined
    )
