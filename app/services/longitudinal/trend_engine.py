"""Wellness Trend Engine to compute deterministic trends over time."""

from typing import Sequence
from app.schemas.longitudinal import InsightConfidence, TrendDirection, WellnessTrend, TrackingCompleteness
from app.models.energy_log import EnergyLog
from app.models.mood_log import MoodLog
from app.models.activity import ActivityLog
from app.models.nutrition import NutritionLog

class WellnessTrendEngine:
    
    @staticmethod
    def _calculate_direction(current: float | None, previous: float | None, threshold: float = 0.05) -> TrendDirection:
        if current is None or previous is None:
            return TrendDirection.INSUFFICIENT_DATA
        if previous == 0:
            return TrendDirection.INCREASING if current > 0 else TrendDirection.STABLE
        
        pct_change = (current - previous) / abs(previous)
        if pct_change > threshold:
            return TrendDirection.INCREASING
        elif pct_change < -threshold:
            return TrendDirection.DECREASING
        else:
            return TrendDirection.STABLE

    @staticmethod
    def _get_confidence(samples: int, min_samples: int = 3) -> InsightConfidence:
        if samples < min_samples:
            return InsightConfidence.INSUFFICIENT_DATA
        if samples < min_samples * 2:
            return InsightConfidence.LOW
        if samples < min_samples * 4:
            return InsightConfidence.MEDIUM
        return InsightConfidence.HIGH

    @staticmethod
    def analyze_energy_trend(current_logs: Sequence[EnergyLog], previous_logs: Sequence[EnergyLog]) -> WellnessTrend:
        curr_avg = sum(log.energy_level for log in current_logs) / len(current_logs) if current_logs else None
        prev_avg = sum(log.energy_level for log in previous_logs) / len(previous_logs) if previous_logs else None
        
        return WellnessTrend(
            domain="energy",
            metric="average_energy",
            direction=WellnessTrendEngine._calculate_direction(curr_avg, prev_avg),
            current_value=round(curr_avg, 2) if curr_avg else None,
            previous_value=round(prev_avg, 2) if prev_avg else None,
            unit="/ 5",
            confidence=WellnessTrendEngine._get_confidence(len(current_logs))
        )

    @staticmethod
    def analyze_activity_trend(current_logs: Sequence[ActivityLog], previous_logs: Sequence[ActivityLog]) -> WellnessTrend:
        curr_total = sum(log.duration_minutes for log in current_logs) if current_logs else 0
        prev_total = sum(log.duration_minutes for log in previous_logs) if previous_logs else 0
        
        if not current_logs and not previous_logs:
            return WellnessTrend(
                domain="activity",
                metric="total_duration",
                direction=TrendDirection.INSUFFICIENT_DATA,
                confidence=InsightConfidence.INSUFFICIENT_DATA
            )
            
        return WellnessTrend(
            domain="activity",
            metric="total_duration",
            direction=WellnessTrendEngine._calculate_direction(curr_total, prev_total),
            current_value=curr_total,
            previous_value=prev_total,
            unit="minutes",
            confidence=WellnessTrendEngine._get_confidence(len(current_logs), min_samples=2)
        )

    @staticmethod
    def calculate_completeness(
        days: int,
        energy_count: int,
        mood_count: int,
        symptom_count: int,
        activity_count: int,
        nutrition_count: int
    ) -> TrackingCompleteness:
        
        if days == 0:
            return TrackingCompleteness(overall_score=0, domain_scores={}, days_in_range=0)
            
        scores = {
            "energy": min(1.0, energy_count / days),
            "mood": min(1.0, mood_count / days),
            "symptoms": min(1.0, symptom_count / days),
            "activity": min(1.0, activity_count / days),
            "nutrition": min(1.0, nutrition_count / days),
        }
        
        overall = sum(scores.values()) / len(scores)
        
        return TrackingCompleteness(
            overall_score=round(overall, 2),
            domain_scores={k: round(v, 2) for k, v in scores.items()},
            days_in_range=days
        )
