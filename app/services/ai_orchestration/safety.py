import enum
from typing import List
from pydantic import BaseModel

class SafetyRiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    LOW_RISK_HEALTH = "LOW_RISK_HEALTH"
    HIGH_RISK_MEDICAL = "HIGH_RISK_MEDICAL"
    URGENT_EMERGENCY = "URGENT_EMERGENCY"
    TEEN_RESTRICTED = "TEEN_RESTRICTED"

class SafetyValidationResult(BaseModel):
    is_safe: bool
    risk_level: SafetyRiskLevel
    reason: str = ""
    override_message: str = ""

class HealthSafetyRouter:
    """
    Evaluates queries and responses to enforce medical boundaries.
    """
    
    def validate_pre_generation(self, query: str, user_age: int) -> SafetyValidationResult:
        query_lower = query.lower()
        
        # 1. Emergency Detection
        emergency_keywords = ["suicide", "kill myself", "heart attack", "stroke", "bleeding out", "can't breathe"]
        if any(w in query_lower for w in emergency_keywords):
            return SafetyValidationResult(
                is_safe=False,
                risk_level=SafetyRiskLevel.URGENT_EMERGENCY,
                reason="Potential medical emergency detected.",
                override_message="It sounds like you might be experiencing a medical emergency. Please contact emergency services or go to the nearest hospital immediately."
            )
            
        # 2. High-Risk Medical Advice
        high_risk_keywords = ["cancer", "tumor", "dose", "prescription", "should i stop taking", "diagnose me"]
        if any(w in query_lower for w in high_risk_keywords):
            return SafetyValidationResult(
                is_safe=False,
                risk_level=SafetyRiskLevel.HIGH_RISK_MEDICAL,
                reason="Requesting specific medical diagnosis or prescription advice.",
                override_message="I cannot provide medical diagnoses or advice about prescriptions. Please consult a healthcare professional for these concerns."
            )
            
        # 3. Teen Safety Guardrails
        if 13 <= user_age < 18:
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
            "stop taking your medication"
        ]
        
        if any(phrase in text_lower for phrase in forbidden_phrases):
            return False
            
        return True
