"""Health Context Router to map user intent to required health context scopes."""

from typing import List
from app.services.ai_context.context_builder import ContextScope

class HealthContextRouter:
    """A heuristic-based router to determine required health scopes from a user's question."""
    
    @staticmethod
    def determine_scopes(question: str) -> List[ContextScope]:
        question_lower = question.lower()
        scopes: set[ContextScope] = set()
        
        # Energy heuristics
        if any(word in question_lower for word in ["energy", "tired", "fatigue", "exhausted", "sleep"]):
            scopes.add("ENERGY")
            scopes.add("SYMPTOMS")
            scopes.add("LONGITUDINAL")
            
        # Cycle heuristics
        if any(word in question_lower for word in ["period", "cycle", "menstruation", "ovulation", "flow"]):
            scopes.add("CYCLE")
            
        # Symptom heuristics
        if any(word in question_lower for word in ["symptom", "pain", "cramps", "headache", "ache"]):
            scopes.add("SYMPTOMS")
            scopes.add("LONGITUDINAL")
            
        # Mood heuristics
        if any(word in question_lower for word in ["mood", "sad", "anxious", "happy", "angry", "stressed"]):
            scopes.add("MOOD")
            scopes.add("LONGITUDINAL")
            
        # Nutrition heuristics
        if any(word in question_lower for word in ["food", "eat", "protein", "calories", "nutrition", "diet"]):
            scopes.add("NUTRITION")
            
        # Activity heuristics
        if any(word in question_lower for word in ["activity", "exercise", "workout", "run", "walk", "steps"]):
            scopes.add("ACTIVITY")
            
        # If they ask about trends or patterns explicitly
        if any(word in question_lower for word in ["trend", "pattern", "recently", "lately", "history", "usually"]):
            scopes.add("LONGITUDINAL")
            
        # If we couldn't determine anything specific, but it might be a general health question, we return an empty list.
        # General knowledge questions won't get personal data.
        return list(scopes)
