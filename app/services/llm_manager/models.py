from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ProviderName(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    RULE_BASED = "rule-based"

class TaskType(str, Enum):
    CONTENT_GENERATION = "CONTENT_GENERATION"
    TRANSLATION = "TRANSLATION"
    FACT_VALIDATION = "FACT_VALIDATION"
    TRANSLATION_VALIDATION = "TRANSLATION_VALIDATION"
    RESEARCH_EXTRACTION = "RESEARCH_EXTRACTION"
    GENERAL = "GENERAL"

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class LLMResponse(BaseModel):
    content: str
    provider_used: ProviderName
    model_used: str
    usage: TokenUsage
    estimated_cost: float = 0.0
    structured_data: Optional[Dict[str, Any]] = None

