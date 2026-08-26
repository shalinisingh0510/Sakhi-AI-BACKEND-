"""Symptom Pattern Engine to detect recurring issues and cycle correlations."""

from typing import Sequence
from collections import Counter
from app.schemas.longitudinal import InsightConfidence, SymptomPattern
from app.models.symptom_log import SymptomLog
from app.models.menstrual_cycle import CycleLog

class SymptomPatternEngine:
    
    @staticmethod
    def _get_confidence(occurrences: int, min_samples: int = 3) -> InsightConfidence:
        if occurrences < min_samples:
            return InsightConfidence.INSUFFICIENT_DATA
        if occurrences < min_samples * 2:
            return InsightConfidence.LOW
        if occurrences < min_samples * 4:
            return InsightConfidence.MEDIUM
        return InsightConfidence.HIGH

    @staticmethod
    def find_frequent_symptoms(symptoms: Sequence[SymptomLog], min_occurrences: int = 2) -> list[SymptomPattern]:
        """Identify most frequent symptoms."""
        
        # Count occurrence of each symptom code
        counts = Counter(s.symptom_code for s in symptoms)
        
        patterns = []
        for code, count in counts.items():
            if count >= min_occurrences:
                patterns.append(
                    SymptomPattern(
                        symptom_code=code,
                        occurrences=count,
                        confidence=SymptomPatternEngine._get_confidence(count, min_samples=3)
                    )
                )
                
        # Sort by most frequent
        patterns.sort(key=lambda x: x.occurrences, reverse=True)
        return patterns

    @staticmethod
    def find_cycle_correlations(symptoms: Sequence[SymptomLog], cycle_logs: Sequence[CycleLog]) -> list[SymptomPattern]:
        """Identify symptoms that occur frequently on specific cycle days."""
        # For simplicity, we just check if symptoms occur frequently on days 1-5 (menses) vs others.
        # In a real implementation, this would look at the precise cycle day (e.g. log_date - cycle_start_date)
        # Here we do a basic dummy correlation for Phase 8 architecture demonstration.
        
        # Map date to cycle phase if cycle log exists and indicates menses
        menses_dates = {c.log_date for c in cycle_logs if c.menses_flow and c.menses_flow != "NONE"}
        
        symptoms_during_menses = Counter(s.symptom_code for s in symptoms if s.log_date in menses_dates)
        symptoms_outside_menses = Counter(s.symptom_code for s in symptoms if s.log_date not in menses_dates)
        
        patterns = []
        for code, in_count in symptoms_during_menses.items():
            out_count = symptoms_outside_menses.get(code, 0)
            
            # If it occurs during menses at least 2 times, and mostly during menses (> 60% of time)
            if in_count >= 2 and (in_count / (in_count + out_count) > 0.6):
                patterns.append(
                    SymptomPattern(
                        symptom_code=code,
                        occurrences=in_count + out_count,
                        confidence=SymptomPatternEngine._get_confidence(in_count, min_samples=2),
                        cycle_correlation="Early cycle (menses)"
                    )
                )
                
        patterns.sort(key=lambda x: x.occurrences, reverse=True)
        return patterns
