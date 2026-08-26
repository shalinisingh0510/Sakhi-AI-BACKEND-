from enum import Enum
from typing import Any
from pydantic import BaseModel

class TrendDirection(str, Enum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    VARIABLE = "VARIABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class InsightConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class WellnessTrend(BaseModel):
    domain: str
    metric: str
    direction: TrendDirection
    current_value: float | None = None
    previous_value: float | None = None
    unit: str | None = None
    confidence: InsightConfidence

class TrackingCompleteness(BaseModel):
    overall_score: float
    domain_scores: dict[str, float]
    days_in_range: int

class SymptomPattern(BaseModel):
    symptom_code: str
    occurrences: int
    confidence: InsightConfidence
    cycle_correlation: str | None = None # e.g. "cycle days 1-4"
