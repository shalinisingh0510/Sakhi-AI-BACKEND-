import logging
import time
from typing import Dict, List, Optional, Type, TypeVar, Any
from pydantic import BaseModel

from app.core.config import Settings
from app.services.llm_manager.models import ProviderName, TaskType, LLMResponse
from app.services.llm_manager.providers.base import LLMProvider, ProviderException, RateLimitException
from app.services.llm_manager.providers.openai_compatible import OpenAICompatibleProvider
from app.services.llm_manager.providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class ProviderState:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.failures = 0
        self.last_failure_time = 0.0

class LLMProviderManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: Dict[ProviderName, ProviderState] = {}
        self._initialize_providers(settings)
        
        # Default priority: user's primary, then fallback list
        self.default_priority: List[ProviderName] = []
        if settings.llm_primary_provider in ProviderName._value2member_map_:
            self.default_priority.append(ProviderName(settings.llm_primary_provider))
            
        for p in settings.llm_fallback_providers:
            if p in ProviderName._value2member_map_ and ProviderName(p) not in self.default_priority:
                self.default_priority.append(ProviderName(p))
                
        # Hardcoded task routing (could be moved to config)
        self.task_routing: Dict[TaskType, List[ProviderName]] = {
            TaskType.CONTENT_GENERATION: [ProviderName.GEMINI, ProviderName.DEEPSEEK, ProviderName.QWEN, ProviderName.OPENROUTER, ProviderName.GROQ],
            TaskType.TRANSLATION: [ProviderName.GEMINI, ProviderName.QWEN, ProviderName.DEEPSEEK, ProviderName.OPENROUTER, ProviderName.GROQ],
            TaskType.FACT_VALIDATION: [ProviderName.DEEPSEEK, ProviderName.GEMINI, ProviderName.QWEN, ProviderName.OPENROUTER, ProviderName.GROQ],
            TaskType.TRANSLATION_VALIDATION: [ProviderName.DEEPSEEK, ProviderName.GEMINI, ProviderName.QWEN, ProviderName.OPENROUTER, ProviderName.GROQ],
        }

    def _initialize_providers(self, settings: Settings):
        # Gemini
        if settings.gemini_api_key:
            self.providers[ProviderName.GEMINI] = ProviderState(GeminiProvider(
                api_key=settings.gemini_api_key.get_secret_value(),
                model_name="gemini-1.5-flash"
            ))
            
        # Groq
        if settings.groq_api_key:
            self.providers[ProviderName.GROQ] = ProviderState(OpenAICompatibleProvider(
                name=ProviderName.GROQ,
                api_key=settings.groq_api_key.get_secret_value(),
                base_url="https://api.groq.com/openai/v1",
                model_name="openai/gpt-oss-20b" # Free tier fast model
            ))
            
        # OpenRouter
        if settings.openrouter_api_key:
            self.providers[ProviderName.OPENROUTER] = ProviderState(OpenAICompatibleProvider(
                name=ProviderName.OPENROUTER,
                api_key=settings.openrouter_api_key.get_secret_value(),
                base_url="https://openrouter.ai/api/v1",
                model_name=settings.openrouter_free_model_1
            ))
            
        # DeepSeek
        if settings.deepseek_api_key:
            self.providers[ProviderName.DEEPSEEK] = ProviderState(OpenAICompatibleProvider(
                name=ProviderName.DEEPSEEK,
                api_key=settings.deepseek_api_key.get_secret_value(),
                base_url="https://api.deepseek.com",
                model_name=settings.deepseek_model
            ))
            
        # Qwen
        if settings.qwen_api_key:
            self.providers[ProviderName.QWEN] = ProviderState(OpenAICompatibleProvider(
                name=ProviderName.QWEN,
                api_key=settings.qwen_api_key.get_secret_value(),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model_name=settings.qwen_model
            ))

    def _get_provider_chain(self, task: TaskType) -> List[LLMProvider]:
        priority = self.task_routing.get(task, self.default_priority)
        chain = []
        for p_name in priority:
            if p_name in self.providers:
                state = self.providers[p_name]
                # Check circuit breaker
                if state.failures >= self.settings.llm_circuit_breaker_failures:
                    if time.time() - state.last_failure_time > self.settings.llm_circuit_breaker_cooldown_seconds:
                        # Reset for trial
                        state.failures = 0
                    else:
                        continue # Skip due to circuit breaker
                
                if state.provider.is_healthy():
                    chain.append(state.provider)
        return chain

    def _record_failure(self, provider_name: ProviderName):
        if provider_name in self.providers:
            state = self.providers[provider_name]
            state.failures += 1
            state.last_failure_time = time.time()
            logger.warning(f"Provider {provider_name} recorded a failure. Total failures: {state.failures}")

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        task: TaskType = TaskType.GENERAL,
        temperature: float = 0.4,
        max_tokens: int = 2000
    ) -> LLMResponse:
        chain = self._get_provider_chain(task)
        if not chain:
            raise Exception("No healthy providers available for this task.")

        errors = []
        for provider in chain:
            # We try each provider with a few retries (for RateLimit or JSON parsing errors)
            attempts = 0
            while attempts < self.settings.llm_max_retries:
                attempts += 1
                try:
                    logger.info(f"[LLMManager] Task: {task.value} | Provider: {provider.name} | Attempt: {attempts}")
                    response = provider.generate_structured(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    # Success
                    self.providers[provider.name].failures = 0
                    return response
                except RateLimitException as e:
                    logger.warning(f"Rate limit hit on {provider.name}: {e}")
                    time.sleep(2 ** attempts) # Exponential backoff
                except ProviderException as e:
                    err_msg = str(e)
                    logger.warning(f"Provider error on {provider.name}: {err_msg}")
                    if "validation" in err_msg.lower() or "parse" in err_msg.lower():
                        # JSON parsing failed, try to add repair instruction to prompt
                        user_prompt += "\n\nWARNING: Your previous response was invalid JSON. Ensure you return ONLY a valid JSON object matching the schema."
                    else:
                        # Other provider errors (auth, server error) break out of the retry loop to fallback immediately
                        self._record_failure(provider.name)
                        errors.append(f"{provider.name}: {e}")
                        break
                except Exception as e:
                    self._record_failure(provider.name)
                    errors.append(f"{provider.name}: {e}")
                    break
            else:
                # Max retries exhausted
                self._record_failure(provider.name)
                errors.append(f"{provider.name}: Max retries exhausted")
                
        raise Exception(f"All providers failed for task {task}. Errors: {errors}")

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        task: TaskType = TaskType.GENERAL,
        temperature: float = 0.4,
        max_tokens: int = 2000
    ) -> LLMResponse:
        chain = self._get_provider_chain(task)
        if not chain:
            raise Exception("No healthy providers available for this task.")

        errors = []
        for provider in chain:
            attempts = 0
            while attempts < self.settings.llm_max_retries:
                attempts += 1
                try:
                    logger.info(f"[LLMManager] Task: {task.value} | Provider: {provider.name} | Attempt: {attempts}")
                    response = provider.generate_text(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    self.providers[provider.name].failures = 0
                    return response
                except RateLimitException as e:
                    logger.warning(f"Rate limit hit on {provider.name}: {e}")
                    time.sleep(2 ** attempts)
                except ProviderException as e:
                    self._record_failure(provider.name)
                    errors.append(f"{provider.name}: {e}")
                    break
                except Exception as e:
                    self._record_failure(provider.name)
                    errors.append(f"{provider.name}: {e}")
                    break
            else:
                self._record_failure(provider.name)
                errors.append(f"{provider.name}: Max retries exhausted")
                
        raise Exception(f"All providers failed for task {task}. Errors: {errors}")

    def get_provider_status(self) -> Dict[str, str]:
        status = {}
        # Iterate over all known providers
        for p in ProviderName:
            if p == ProviderName.RULE_BASED:
                continue
            if p in self.providers:
                state = self.providers[p]
                if not state.provider.is_healthy():
                    status[p.value] = "UNHEALTHY (Auth or Init Error)"
                elif state.failures >= self.settings.llm_circuit_breaker_failures:
                    if time.time() - state.last_failure_time > self.settings.llm_circuit_breaker_cooldown_seconds:
                        status[p.value] = "COOLDOWN_FINISHED (Will Retry)"
                    else:
                        status[p.value] = f"CIRCUIT_BROKEN ({state.failures} failures)"
                else:
                    status[p.value] = "HEALTHY"
            else:
                status[p.value] = "MISSING_KEY_OR_NOT_CONFIGURED"
        return status
