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

    def __init__(self, api_key: str | None = None, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini embeddings may fail if called without key.")
        else:
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


def get_embedding_provider(provider_type: str | None = None) -> EmbeddingProvider:
    """
    Factory to return the configured embedding provider.
    Falls back to MockEmbeddingProvider if no API key is present.
    """
    forced_type = (provider_type or os.getenv("EMBEDDING_PROVIDER", "")).lower()

    if forced_type == "mock":
        return MockEmbeddingProvider()

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            return GeminiEmbeddingProvider(api_key=gemini_key)
        except Exception as e:
            logger.warning(f"Failed to initialize GeminiEmbeddingProvider ({e}), falling back to mock.")

    return MockEmbeddingProvider()
