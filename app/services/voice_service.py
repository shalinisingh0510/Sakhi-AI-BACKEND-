import logging
from typing import Protocol
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class SpeechToTextService(Protocol):
    def transcribe(self, audio_file_path: str, filename: str, language: str | None = None) -> str:
        ...

class MockSTTService:
    def transcribe(self, audio_file_path: str, filename: str, language: str | None = None) -> str:
        logger.info(f"Mock STT transcribing {filename} (lang={language}) from {audio_file_path}")
        return "मुझे पिछले दो महीने से पीरियड अनियमित हो रहे हैं"

class OpenAICompatibleSTTService:
    def __init__(self, api_key: str, base_url: str | None, model: str):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model

    def transcribe(self, audio_file_path: str, filename: str, language: str | None = None) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            with open(audio_file_path, "rb") as f:
                # the openai client requires file to have a name attribute, which `open` provides
                params = {
                    "model": self.model,
                    "file": f
                }
                if language:
                    # Whisper expects language in ISO-639-1 format
                    params["language"] = language

                response = client.audio.transcriptions.create(**params)
                return response.text
        except Exception as e:
            logger.error(f"STT API Error: {e}", exc_info=True)
            raise RuntimeError("Transcription failed due to provider error.") from e

def get_stt_service() -> SpeechToTextService:
    settings = get_settings()
    provider = settings.stt_provider.strip().lower()
    
    if provider == "groq":
        api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
        if not api_key:
            logger.warning("Groq API key missing. Falling back to Mock STT.")
            return MockSTTService()
        return OpenAICompatibleSTTService(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            model=settings.stt_model
        )
    elif provider == "openai":
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        if not api_key:
            logger.warning("OpenAI API key missing. Falling back to Mock STT.")
            return MockSTTService()
        return OpenAICompatibleSTTService(
            api_key=api_key,
            base_url=None,
            model=settings.stt_model
        )
    else:
        return MockSTTService()

