import json
import logging
from typing import Type, TypeVar, Any
from pydantic import BaseModel

try:
    from openai import OpenAI, RateLimitError, APITimeoutError, APIError, AuthenticationError
except ImportError:
    OpenAI = None  # type: ignore

from app.services.llm_manager.models import LLMResponse, ProviderName, TokenUsage
from app.services.llm_manager.providers.base import LLMProvider, ProviderException, RateLimitException

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: ProviderName, api_key: str, base_url: str, model_name: str):
        self.name = name
        self.model_name = model_name
        self._is_healthy = True
        
        if not OpenAI:
            logger.error("openai package not installed.")
            self._is_healthy = False
            self.client = None
            return

        if not api_key:
            self._is_healthy = False
            self.client = None
            return

        try:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for {name}: {e}")
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
            raise ProviderException(f"Provider {self.name} is not initialized or healthy.")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content or ""
            usage = TokenUsage()
            if response.usage:
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
                
            return LLMResponse(
                content=content,
                provider_used=self.name,
                model_used=self.model_name,
                usage=usage
            )
        except RateLimitError as e:
            raise RateLimitException(f"Rate limit exceeded on {self.name}: {e}")
        except AuthenticationError as e:
            self._is_healthy = False
            raise ProviderException(f"Authentication error on {self.name}: {e}")
        except Exception as e:
            raise ProviderException(f"API error on {self.name}: {e}")

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.4,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.client:
            raise ProviderException(f"Provider {self.name} is not initialized or healthy.")

        try:
            # We attempt standard JSON mode with instructions in prompt
            schema_json = json.dumps(response_model.model_json_schema(), indent=2)
            sys_prompt_augmented = system_prompt + f"\n\nYou MUST return only a valid JSON object matching the EXACT following schema:\n{schema_json}"
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": sys_prompt_augmented},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content or ""
            usage = TokenUsage()
            if response.usage:
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
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
                raise ProviderException(f"Failed to parse or validate JSON from {self.name}: {e}\nContent: {content}")
                
        except RateLimitError as e:
            raise RateLimitException(f"Rate limit exceeded on {self.name}: {e}")
        except AuthenticationError as e:
            self._is_healthy = False
            raise ProviderException(f"Authentication error on {self.name}: {e}")
        except Exception as e:
            raise ProviderException(f"API error on {self.name}: {e}")
