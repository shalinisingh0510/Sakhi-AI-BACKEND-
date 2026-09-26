"""
Gemini provider using the new google-genai SDK (google.genai).
Replaces the deprecated google.generativeai package.
"""
import json
import logging
from typing import Type, TypeVar, Any
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GENAI_AVAILABLE = False

from app.services.llm_manager.models import LLMResponse, ProviderName, TokenUsage
from app.services.llm_manager.providers.base import LLMProvider, ProviderException, RateLimitException

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.name = ProviderName.GEMINI
        self.model_name = model_name
        self._is_healthy = True

        if not GENAI_AVAILABLE:
            logger.error("google-genai package not installed. Run: pip install google-genai")
            self._is_healthy = False
            self.client = None
            return

        if not api_key:
            self._is_healthy = False
            self.client = None
            return

        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self._is_healthy = False
            self.client = None

    def is_healthy(self) -> bool:
        return self._is_healthy

    def _build_contents(self, system_prompt: str, user_prompt: str) -> list:
        return [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}")]
            )
        ]

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 2000
    ) -> LLMResponse:
        if not self.client:
            raise ProviderException("Gemini client is not initialized or healthy.")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self._build_contents(system_prompt, user_prompt),
                config=genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            content = response.text or ""
            usage = TokenUsage()
            if response.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                    completion_tokens=response.usage_metadata.candidates_token_count or 0,
                    total_tokens=response.usage_metadata.total_token_count or 0,
                )

            return LLMResponse(
                content=content,
                provider_used=self.name,
                model_used=self.model_name,
                usage=usage,
            )

        except Exception as e:
            err = str(e)
            if "429" in err or "503" in err or "500" in err or "502" in err or "504" in err or "quota" in err.lower() or "rate" in err.lower() or "unavailable" in err.lower() or "high demand" in err.lower() or "overloaded" in err.lower():
                raise RateLimitException(f"Gemini transient error/rate limit: {e}")
            if "403" in err or "permission" in err.lower() or "api_key" in err.lower():
                self._is_healthy = False
                raise ProviderException(f"Gemini auth error: {e}")
            raise ProviderException(f"Gemini API error: {e}")

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.4,
        max_tokens: int = 4000
    ) -> LLMResponse:
        if not self.client:
            raise ProviderException("Gemini client is not initialized or healthy.")

        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        augmented_prompt = (
            f"SYSTEM:\n{system_prompt}\n\n"
            f"You MUST return ONLY a valid JSON object matching this schema:\n{schema_json}\n\n"
            f"USER:\n{user_prompt}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part(text=augmented_prompt)]
                    )
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                ),
            )

            content = response.text or ""
            usage = TokenUsage()
            if response.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                    completion_tokens=response.usage_metadata.candidates_token_count or 0,
                    total_tokens=response.usage_metadata.total_token_count or 0,
                )

            try:
                parsed = json.loads(content)
                obj = response_model.model_validate(parsed)
                return LLMResponse(
                    content=content,
                    provider_used=self.name,
                    model_used=self.model_name,
                    usage=usage,
                    structured_data=obj.model_dump(),
                )
            except Exception as e:
                raise ProviderException(
                    f"Failed to parse/validate JSON from Gemini: {e}\nContent: {content[:500]}"
                )

        except ProviderException:
            raise
        except Exception as e:
            err = str(e)
            if "429" in err or "503" in err or "500" in err or "502" in err or "504" in err or "quota" in err.lower() or "rate" in err.lower() or "unavailable" in err.lower() or "high demand" in err.lower() or "overloaded" in err.lower():
                raise RateLimitException(f"Gemini transient error/rate limit: {e}")
            if "403" in err or "permission" in err.lower() or "api_key" in err.lower():
                self._is_healthy = False
                raise ProviderException(f"Gemini auth error: {e}")
            raise ProviderException(f"Gemini API error: {e}")
