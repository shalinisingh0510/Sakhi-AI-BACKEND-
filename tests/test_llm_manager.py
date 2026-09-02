import pytest
from app.services.llm_manager.manager import LLMProviderManager, TaskType
from app.services.llm_manager.models import ProviderName
from app.core.config import get_settings

def test_llm_manager_initialization():
    settings = get_settings()
    manager = LLMProviderManager(settings)
    assert manager is not None
    assert isinstance(manager.providers, dict)

def test_llm_manager_provider_chain():
    settings = get_settings()
    manager = LLMProviderManager(settings)
    chain = manager._get_provider_chain(TaskType.GENERAL)
    # Ensure it returns a list of providers
    assert isinstance(chain, list)
    
def test_provider_status():
    settings = get_settings()
    manager = LLMProviderManager(settings)
    status = manager.get_provider_status()
    assert ProviderName.GEMINI.value in status
    assert ProviderName.GROQ.value in status
    assert ProviderName.OPENROUTER.value in status

