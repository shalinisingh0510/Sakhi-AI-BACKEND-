import enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IntentCategory(str, enum.Enum):
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"       # RAG only (e.g. "What is PMS?")
    PERSONAL_HEALTH = "PERSONAL_HEALTH"           # Context only (e.g. "How is my energy?")
    COMBINED = "COMBINED"                         # RAG + Context (e.g. "Why am I tired around my period?")
    GREETING = "GREETING"                         # Basic chat (e.g. "Hi")
    UNKNOWN = "UNKNOWN"

class ContextScope(str, enum.Enum):
    PROFILE = "PROFILE"
    CYCLE = "CYCLE"
    SYMPTOMS = "SYMPTOMS"
    MOOD = "MOOD"
    ENERGY = "ENERGY"
    NUTRITION = "NUTRITION"
    ACTIVITY = "ACTIVITY"
    LONGITUDINAL_TRENDS = "LONGITUDINAL_TRENDS"

class IntentResult(BaseModel):
    category: IntentCategory
    required_scopes: List[ContextScope]
    search_queries: List[str] = []

class IntentRouter:
    """
    Determines what kind of knowledge/context is needed to answer a user's query.
    In production, this could use a fast, small LLM or heuristic keyword matching.
    """
    def route(self, query: str) -> IntentResult:
        query_lower = query.lower()
        scopes = set()
        category = IntentCategory.UNKNOWN
        search_queries = []
        
        # Simple heuristic mapping for demonstration
        if any(w in query_lower for w in ["energy", "tired", "fatigue", "exhausted"]):
            scopes.update([ContextScope.ENERGY, ContextScope.SYMPTOMS, ContextScope.LONGITUDINAL_TRENDS])
            
        if any(w in query_lower for w in ["period", "cycle", "ovulation", "cramps"]):
            scopes.update([ContextScope.CYCLE, ContextScope.SYMPTOMS])
            
        if any(w in query_lower for w in ["food", "eat", "protein", "calories", "diet"]):
            scopes.update([ContextScope.NUTRITION])
            
        if any(w in query_lower for w in ["workout", "exercise", "walk", "activity"]):
            scopes.update([ContextScope.ACTIVITY])
            
        # Determine Category
        has_personal_pronouns = any(w in query_lower for w in [" i ", " my ", " me "])
        is_general_question = any(w in query_lower for w in ["what is", "how do", "why do people", "symptoms of"])
        
        if has_personal_pronouns and is_general_question:
            category = IntentCategory.COMBINED
            search_queries.append(query)
        elif has_personal_pronouns and scopes:
            category = IntentCategory.PERSONAL_HEALTH
        elif is_general_question:
            category = IntentCategory.GENERAL_KNOWLEDGE
            search_queries.append(query)
        elif not scopes:
            category = IntentCategory.GREETING
        else:
            category = IntentCategory.COMBINED
            
        return IntentResult(
            category=category,
            required_scopes=list(scopes),
            search_queries=search_queries
        )
