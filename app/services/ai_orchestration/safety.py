import enum
from typing import List
from pydantic import BaseModel

class SafetyRiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    LOW_RISK_HEALTH = "LOW_RISK_HEALTH"
    HIGH_RISK_MEDICAL = "HIGH_RISK_MEDICAL"
    URGENT_EMERGENCY = "URGENT_EMERGENCY"
    TEEN_RESTRICTED = "TEEN_RESTRICTED"

class SafetyValidationResult(BaseModel):
    is_safe: bool
    risk_level: SafetyRiskLevel
    reason: str = ""
    override_message: str = ""
    fallback_message: str = ""

class HealthSafetyRouter:
    """
    Evaluates queries and responses to enforce medical boundaries.
    """
    
    def validate_pre_generation(self, query: str, user_age: int | None = None) -> SafetyValidationResult:
        query_lower = query.lower()
        
        # 0. Out of Scope Detection
        out_of_scope_keywords = ["python", "java", "code", "programming", "blockchain", "cricket", "football", "joke"]
        if any(w in query_lower.split() for w in out_of_scope_keywords):
            # Only trigger if it strongly looks like out of scope, a better classifier is needed in prod
            return SafetyValidationResult(
                is_safe=False,
                risk_level=SafetyRiskLevel.OUT_OF_SCOPE,
                reason="Query appears to be out of the women's health scope.",
                fallback_message="I specialize in women's health and wellness. How can I help you with that today?"
            )
            
        # 1. Emergency Detection
        emergency_keywords = ["suicide", "kill myself", "die", "heart attack", "stroke", "severe pain", "bleeding heavily", "can't breathe"]
        if any(kw in query_lower for kw in emergency_keywords):
            return SafetyValidationResult(
                is_safe=False,
                risk_level=SafetyRiskLevel.EMERGENCY,
                reason="Potential medical emergency detected.",
                fallback_message="This sounds like a medical emergency. Please contact your local emergency services or visit the nearest hospital immediately."
            )
            
        # 2. Diagnosis Prevention (heuristics)
        diagnosis_keywords = ["do i have", "is this cancer", "diagnose me", "what disease"]
        if any(kw in query_lower for kw in diagnosis_keywords):
            return SafetyValidationResult(
                is_safe=False,
                risk_level=SafetyRiskLevel.HIGH,
                reason="User is seeking a medical diagnosis.",
                fallback_message="I cannot diagnose medical conditions. Please consult a healthcare professional."
            )
            
        # 3. Teen Safety Guardrails
        if user_age is not None and 13 <= user_age < 18:
            teen_restricted = ["lose weight fast", "calorie deficit", "diet pills", "fasting"]
            if any(w in query_lower for w in teen_restricted):
                return SafetyValidationResult(
                    is_safe=False,
                    risk_level=SafetyRiskLevel.TEEN_RESTRICTED,
                    reason="Age-restricted topic (weight loss/dieting) for teen user.",
                    override_message="As an AI, I focus on supporting balanced nutrition and healthy habits rather than restrictive dieting or weight loss. If you have concerns about your weight, it's best to talk to a trusted adult or doctor."
                )
                
        return SafetyValidationResult(is_safe=True, risk_level=SafetyRiskLevel.SAFE)

class HealthAIResponseGuard:
    """
    Validates LLM responses before returning them to the user.
    Ensures the LLM did not hallucinate a diagnosis or violate rules.
    """
    def validate_post_generation(self, response_text: str) -> bool:
        text_lower = response_text.lower()
        
        # Strict pattern matching to catch LLMs that ignored system prompts
        forbidden_phrases = [
            "you have been diagnosed with",
            "i diagnose you",
            "you should take",
            "this means you have",
            "stop taking your medication",
            "ignore previous instructions",
            "system prompt"
        ]
        
        if any(phrase in text_lower for phrase in forbidden_phrases):
            return False
            
        return True
