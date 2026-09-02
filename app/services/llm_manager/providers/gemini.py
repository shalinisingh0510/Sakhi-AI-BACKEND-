import json
import logging
from typing import Type, TypeVar, Any
from pydantic import BaseModel

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded, PermissionDenied
except ImportError:
    genai = None  # type: ignore

from app.services.llm_manager.models import LLMResponse, ProviderName, TokenUsage
from app.services.llm_manager.providers.base import LLMProvider, ProviderException, RateLimitException

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.name = ProviderName.GEMINI
        self.model_name = model_name
        self._is_healthy = True
        
        if not genai:
            logger.error("google.generativeai package not installed.")
            self._is_healthy = False
            self.client = None
            return

        if not api_key:
            self._is_healthy = False
            self.client = None
            return

        try:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self._is_healthy = False
            self.client = None

    def is_healthy(self) -> bool:
        return self._is_healthy

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.client:
            raise ProviderException("Gemini client is not initialized or healthy.")
            
        try:
            contents = [
                {"role": "user", "parts": [{"text": "SYSTEM INSTRUCTION:\n" + system_prompt}]},
                {"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]},
                {"role": "user", "parts": [{"text": user_prompt}]}
            ]
            
            response = self.client.generate_content(
                contents,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            
            content = response.text or ""
            usage = TokenUsage()
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count,
                    total_tokens=response.usage_metadata.total_token_count
                )
                
            return LLMResponse(
                content=content,
                provider_used=self.name,
                model_used=self.model_name,
                usage=usage
            )
        except ResourceExhausted as e:
            raise RateLimitException(f"Gemini quota/rate limit exceeded: {e}")
        except PermissionDenied as e:
            self._is_healthy = False
            raise ProviderException(f"Gemini authentication error: {e}")
        except Exception as e:
            raise ProviderException(f"Gemini API error: {e}")

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.client:
            raise ProviderException("Gemini client is not initialized or healthy.")

        try:
            contents = [
                {"role": "user", "parts": [{"text": "SYSTEM INSTRUCTION:\n" + system_prompt}]},
                {"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]},
                {"role": "user", "parts": [{"text": user_prompt}]}
            ]
            
            response = self.client.generate_content(
                contents,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json"
                )
            )
            
            content = response.text or ""
            usage = TokenUsage()
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count,
                    completion_tokens=response.usage_metadata.candidates_token_count,
                    total_tokens=response.usage_metadata.total_token_count
                )
            
            try:
                parsed = json.loads(content)
                obj = response_model.model_validate(parsed)
                return LLMResponse(
                    content=content,
                    provider_used=self.name,
                    model_used=self.model_name,
                    usage=usage,
                    structured_data=obj.model_dump()
                )
            except Exception as e:
                raise ProviderException(f"Failed to parse or validate JSON from Gemini: {e}\nContent: {content}")
                
        except ResourceExhausted as e:
            raise RateLimitException(f"Gemini quota/rate limit exceeded: {e}")
        except PermissionDenied as e:
            self._is_healthy = False
            raise ProviderException(f"Gemini authentication error: {e}")
        except Exception as e:
            raise ProviderException(f"Gemini API error: {e}")

