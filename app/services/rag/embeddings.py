from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import List, Protocol

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """
    Protocol for generating text embeddings.
    Allows swapping between Gemini, OpenAI, or local/mock models.
    """
    dimension: int

    def embed_text(self, text: str) -> List[float]:
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...


class MockEmbeddingProvider:
    """
    Deterministic pseudo-embedding provider for testing, development,
    and offline execution without external API dependencies.
    Produces normalized vectors of dimension 768 with term-overlap sensitivity.
    """
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        words = [w.strip(".,!?;:#*()") for w in text.lower().split() if len(w.strip(".,!?;:#*()")) > 2]
        if not words:
            words = ["empty"]

        for word in words:
            for i in range(16):
                idx = int(hashlib.md5(f"{word}:{i}".encode("utf-8")).hexdigest()[:4], 16) % self.dimension
                vector[idx] += 1.0

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class GeminiEmbeddingProvider:
    """
    Implementation of EmbeddingProvider using Google Gemini API.
    """
    dimension = 768

    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
        except ImportError:
            logger.warning("google-generativeai is not installed.")
        self.model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        import google.generativeai as genai
        response = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_document",
        )
        return response["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        import google.generativeai as genai
        response = genai.embed_content(
            model=self.model_name,
            content=texts,
            task_type="retrieval_document",
        )
        return response["embedding"]


class OpenAIEmbeddingProvider:
    """
    Implementation of EmbeddingProvider using OpenAI API.
    """
    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small", dimension: int = 1536):
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            logger.warning("openai is not installed.")
            self.client = None

    def embed_text(self, text: str) -> List[float]:
        if not self.client:
            return [0.0] * self.dimension
        response = self.client.embeddings.create(input=[text], model=self.model_name)
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts or not self.client:
            return []
        response = self.client.embeddings.create(input=texts, model=self.model_name)
        return [data.embedding for data in response.data]


def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory to return the configured embedding provider using app settings.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    provider_type = settings.embedding_provider.lower()

    if provider_type == "openai":
        key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
        if key:
            return OpenAIEmbeddingProvider(api_key=key, model_name=settings.embedding_model, dimension=settings.embedding_dimensions)
            
    elif provider_type == "gemini":
        key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        if key:
            return GeminiEmbeddingProvider(api_key=key, model_name=settings.embedding_model)

    logger.warning("No valid embedding provider config found. Falling back to MockEmbeddingProvider.")
    return MockEmbeddingProvider(dimension=settings.embedding_dimensions)
