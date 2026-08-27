import os
from typing import List, Protocol
import google.generativeai as genai

class EmbeddingProvider(Protocol):
    """
    Protocol for generating text embeddings.
    Allows swapping between Gemini, OpenAI, or local models.
    """
    def embed_text(self, text: str) -> List[float]:
        ...
        
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...

class GeminiEmbeddingProvider:
    """
    Implementation of EmbeddingProvider using Google Gemini API.
    """
    def __init__(self, api_key: str = None, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
            
        genai.configure(api_key=self.api_key)
        self.model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        response = genai.embed_content(
            model=self.model_name,
            content=text,
            task_type="retrieval_document",
        )
        return response['embedding']

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of text strings."""
        if not texts:
            return []
            
        response = genai.embed_content(
            model=self.model_name,
            content=texts,
            task_type="retrieval_document",
        )
        return response['embedding']

def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory to return the configured embedding provider.
    """
    return GeminiEmbeddingProvider()
