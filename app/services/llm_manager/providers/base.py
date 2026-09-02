from typing import Protocol, Optional, Type, TypeVar, Any
from pydantic import BaseModel
from app.services.llm_manager.models import LLMResponse, ProviderName

T = TypeVar("T", bound=BaseModel)

class ProviderException(Exception):
    """Base exception for provider errors."""
    pass

class RateLimitException(ProviderException):
    """Raised when a provider hits a rate limit or quota."""
    pass

class LLMProvider(Protocol):
    name: ProviderName
    
    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> LLMResponse:
        ...

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> LLMResponse:
        ...
        
    def is_healthy(self) -> bool:
        ...

