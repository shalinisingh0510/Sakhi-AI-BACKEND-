import enum
from typing import Optional

class ModelType(str, enum.Enum):
    GEMINI_15_FLASH = "gemini-1.5-flash"
    GEMINI_15_PRO = "gemini-1.5-pro"
    LOCAL_FALLBACK = "local-llama-3"

class AIRoutingService:
    """
    Intelligently routes AI requests based on task complexity, user plan, and cost efficiency.
    Implements fallbacks if the primary provider is unavailable.
    """
    def __init__(self):
        # In a real environment, this might check external latency metrics or circuit breakers
        self.circuit_breaker_active = False

    def get_model_for_task(self, task_type: str, user_plan: str = "FREE") -> str:
        """
        Determines the most appropriate model.
        
        Args:
            task_type: e.g., 'simple_qa', 'medical_reasoning', 'vision', 'longitudinal_summary'
            user_plan: 'FREE' or 'PAID'
        """
        if self.circuit_breaker_active:
            # Fallback to cheapest/local reliable model
            return ModelType.LOCAL_FALLBACK.value
            
        if task_type in ["simple_qa", "vision"]:
            # Flash is fast and cheap for basic reasoning and multimodal
            return ModelType.GEMINI_15_FLASH.value
            
        if task_type in ["medical_reasoning", "longitudinal_summary"]:
            if user_plan == "PAID":
                # Deep reasoning requires larger context and parameter count
                return ModelType.GEMINI_15_PRO.value
            else:
                # Free users still get a safe response, but using the lighter model
                return ModelType.GEMINI_15_FLASH.value
                
        # Default
        return ModelType.GEMINI_15_FLASH.value
