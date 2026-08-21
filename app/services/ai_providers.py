"""
AI provider abstraction for Sakhi AI.

Provides a pluggable reply-generation interface. Four providers are available:

- RuleBasedProvider  — no external dependencies, always works, used in tests.
- OpenAIProvider     — calls the OpenAI Chat Completions API.
- GeminiProvider     — calls the Google Gemini API.
- GroqProvider       — calls the Groq API using the OpenAI SDK.

Select the provider by setting:
  SAKHI_AI_PROVIDER_NAME=rule-based   (default)
  SAKHI_AI_PROVIDER_NAME=gemini
  SAKHI_GEMINI_API_KEY=AIzaSy...
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)

# System prompt used to keep responses safe and educational.
_SYSTEM_PROMPT = """
You are Sakhi, a trusted, compassionate women's and girls' health education assistant.

Your role:
- Provide clear, accurate, culturally sensitive, and age-appropriate health education.
- Focus on menstrual health, reproductive health, hygiene, mental wellness, and general wellbeing.
- Always distinguish educational information from professional medical advice.
- Never diagnose conditions or prescribe treatments.
- When a topic requires professional medical care, say so clearly and compassionately.
- Respond in the user's preferred language when asked.
- Keep responses concise, warm, and empowering.
- End every response with a brief reminder that it is educational and not a medical diagnosis.

Restrictions:
- Do not discuss unrelated topics (politics, entertainment, etc.).
- Do not provide harmful, misleading, or explicit content.
- If a message seems to describe a medical emergency, direct the user to seek immediate help.
"""

_VOICE_MODE_PROMPT = """
CRITICAL INSTRUCTION FOR THIS RESPONSE: The user is communicating via VOICE/AUDIO. 
Keep your response VERY concise, conversational, and spoken-friendly. 
Do NOT use markdown formatting like asterisks (**), bullet points, or complex punctuation that text-to-speech engines struggle with.
"""


class AIProviderProtocol(Protocol):
    """Interface that every AI provider must satisfy."""

    def generate_reply(
        self,
        *,
        user_message: str,
        conversation_title: str,
        preferred_language: str,
        history: list[dict[str, str]],
        mode: str = "text",
    ) -> str:
        """Return an assistant reply string."""
        ...


# ---------------------------------------------------------------------------
# Rule-based provider (no external dependencies)
# ---------------------------------------------------------------------------

_DEFAULT_CONVERSATION_LANGUAGE = "english"


class RuleBasedProvider:
    """Keyword-matched educational responses. Works offline, used in tests."""

    def generate_reply(
        self,
        *,
        user_message: str,
        conversation_title: str,
        preferred_language: str,
        history: list[dict[str, str]],
        mode: str = "text",
    ) -> str:
        message = user_message.lower()
        history_note = f"We are continuing the conversation titled '{conversation_title}'."

        if any(k in message for k in ("period", "menstrual", "cramp", "cycle")):
            body = (
                "Educational guidance: menstrual cramps and cycle changes are common, but severe pain, "
                "heavy bleeding, or dizziness should be reviewed by a qualified clinician. "
                "Gentle rest, hydration, and a heat pack may help."
            )
        elif any(k in message for k in ("pregnan", "baby", "fertility", "ovulation")):
            body = (
                "Educational guidance: questions about fertility and pregnancy deserve careful, personalised "
                "medical advice. If you might be pregnant or have pain, bleeding, or unusual symptoms, "
                "please contact a healthcare professional."
            )
        elif any(k in message for k in ("stress", "anxious", "anxiety", "sad", "mental health")):
            body = (
                "Educational guidance: stress and emotional health matter too. If you feel overwhelmed, "
                "try slow breathing, rest, and reaching out to someone you trust. "
                "If symptoms are persistent or severe, ask a professional for support."
            )
        elif any(k in message for k in ("hygiene", "itch", "discharge", "infection")):
            body = (
                "Educational guidance: changes in discharge, itching, or irritation can have different causes. "
                "Keep the area clean and dry, avoid harsh products, and seek medical advice if symptoms are "
                "painful, persistent, or unusual for you."
            )
        else:
            body = (
                "Educational guidance: I can share trusted health information, explain symptoms in simple terms, "
                "and suggest safe next steps. Tell me more about the main concern and I can keep the guidance "
                "focused and practical."
            )

        language_hint = (
            ""
            if preferred_language == _DEFAULT_CONVERSATION_LANGUAGE
            else f" ({preferred_language})"
        )
        return f"{history_note}{language_hint} {body} This response is educational and not a diagnosis."


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider:
    """Calls the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        try:
            from openai import OpenAI  # type: ignore[import]

            self._client = OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            logger.warning("openai package is not installed.")
            self._client = None  # type: ignore[assignment]
        self._model = model
        self._fallback = RuleBasedProvider()

    def generate_reply(
        self,
        *,
        user_message: str,
        conversation_title: str,
        preferred_language: str,
        history: list[dict[str, str]],
        mode: str = "text",
    ) -> str:
        if self._client is None:
            return self._fallback.generate_reply(
                user_message=user_message,
                conversation_title=conversation_title,
                preferred_language=preferred_language,
                history=history,
                mode=mode,
            )

        system_prompt = _SYSTEM_PROMPT
        if mode == "voice":
            system_prompt += "\n" + _VOICE_MODE_PROMPT

        if preferred_language != _DEFAULT_CONVERSATION_LANGUAGE:
            system_prompt += f"\n\nPlease respond in {preferred_language}."

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=600,
                temperature=0.4,
            )
            reply = response.choices[0].message.content or ""
            if reply.strip():
                return reply.strip()
        except Exception as exc:
            logger.warning(
                "OpenAI API call failed (%s: %s). Falling back to rule-based provider.",
                type(exc).__name__,
                exc,
            )

        return self._fallback.generate_reply(
            user_message=user_message,
            conversation_title=conversation_title,
            preferred_language=preferred_language,
            history=history,
            mode=mode,
        )


# ---------------------------------------------------------------------------
# Groq provider (re-uses OpenAIProvider)
# ---------------------------------------------------------------------------

class GroqProvider(OpenAIProvider):
    """Calls the Groq API using the OpenAI SDK."""
    def __init__(self, api_key: str, model: str = "llama3-8b-8192") -> None:
        super().__init__(api_key=api_key, model=model, base_url="https://api.groq.com/openai/v1")


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider:
    """Calls the Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        try:
            import google.generativeai as genai # type: ignore[import]
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(model)
        except ImportError:
            logger.warning("google-generativeai package is not installed.")
            self._client = None
        self._fallback = RuleBasedProvider()

    def generate_reply(
        self,
        *,
        user_message: str,
        conversation_title: str,
        preferred_language: str,
        history: list[dict[str, str]],
        mode: str = "text",
    ) -> str:
        if self._client is None:
            return self._fallback.generate_reply(
                user_message=user_message,
                conversation_title=conversation_title,
                preferred_language=preferred_language,
                history=history,
                mode=mode,
            )

        system_prompt = _SYSTEM_PROMPT
        if mode == "voice":
            system_prompt += "\n" + _VOICE_MODE_PROMPT

        if preferred_language != _DEFAULT_CONVERSATION_LANGUAGE:
            system_prompt += f"\n\nPlease respond in {preferred_language}."

        try:
            # We can use system_instruction in GenerativeModel directly.
            # But the object is already instantiated. To be safe, we just prepend it.
            # Convert history to Gemini format
            contents = []
            contents.append({"role": "user", "content": f"System Context: {system_prompt}"})
            contents.append({"role": "model", "content": "Understood. I will act as Sakhi and follow those instructions."})
            
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})
            
            contents.append({"role": "user", "parts": [user_message]})
            
            # Note: The above is a simplified conversion. In a real app we'd map properly.
            # Let's map cleanly to Gemini's format:
            formatted_contents = []
            for item in contents:
                formatted_contents.append({"role": item.get("role", "user"), "parts": item.get("parts", [item.get("content", "")])})

            response = self._client.generate_content(
                formatted_contents,
                generation_config={"temperature": 0.4, "max_output_tokens": 600}
            )
            reply = response.text or ""
            if reply.strip():
                return reply.strip()
        except Exception as exc:
            logger.warning(
                "Gemini API call failed (%s: %s). Falling back to rule-based provider.",
                type(exc).__name__,
                exc,
            )

        return self._fallback.generate_reply(
            user_message=user_message,
            conversation_title=conversation_title,
            preferred_language=preferred_language,
            history=history,
            mode=mode,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_ai_provider(settings: Settings) -> AIProviderProtocol:
    """Return the appropriate AI provider based on settings."""
    provider_name = settings.ai_provider_name.strip().lower()

    if provider_name == "openai":
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key is not None
            else ""
        )
        if not api_key:
            return RuleBasedProvider()
        return OpenAIProvider(api_key=api_key, model=settings.openai_model)

    if provider_name == "gemini":
        api_key = (
            settings.gemini_api_key.get_secret_value()
            if settings.gemini_api_key is not None
            else ""
        )
        if not api_key:
            return RuleBasedProvider()
        return GeminiProvider(api_key=api_key)

    if provider_name == "groq":
        api_key = (
            settings.groq_api_key.get_secret_value()
            if settings.groq_api_key is not None
            else ""
        )
        if not api_key:
            return RuleBasedProvider()
        return GroqProvider(api_key=api_key)

    if provider_name != "rule-based":
        logger.warning(
            "Unknown AI provider '%s'. Falling back to rule-based provider.",
            provider_name,
        )
    return RuleBasedProvider()
