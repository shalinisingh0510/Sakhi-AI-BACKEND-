import json
import logging
from typing import List, Optional, Dict
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.knowledge import QueryUnderstandingResult, SearchQuery

logger = logging.getLogger(__name__)

QUERY_UNDERSTANDING_PROMPT = """
You are a medical query understanding module for Sakhi AI, a women's health assistant.
Your task is to analyze the user's latest message and recent conversation history, and generate structured search queries for retrieving trusted medical evidence.

IMPORTANT RULES:
1. Preserve User Intent: Do NOT add medical assumptions. If the user says "pain", do NOT rewrite as "endometriosis pain" unless the context explicitly mentions endometriosis.
2. Terminology Normalization: Map common terms to medical terms without changing meaning (e.g. "heavy periods" -> "menorrhagia" ONLY IF appropriate). If uncertain, preserve original wording.
3. Multi-Query: For complex/ambiguous questions, generate 2-3 search perspectives. For simple factual questions, generate just 1 query.
4. Output JSON ONLY matching the requested schema.

JSON SCHEMA:
{
  "rewritten_query": "The clearest possible standalone version of the user's question.",
  "search_queries": [
    {
      "query": "search query string",
      "is_keyword": false
    }
  ],
  "medical_terms_normalized": {
    "original_term": "normalized_term"
  }
}
"""

class QueryUnderstandingService:
    def __init__(self):
        self.settings = get_settings()
        self._provider = self.settings.ai_provider_name.strip().lower()
        self._client = None
        
        try:
            if self._provider == "gemini":
                import google.generativeai as genai
                if self.settings.gemini_api_key:
                    genai.configure(api_key=self.settings.gemini_api_key.get_secret_value())
                self._client = genai.GenerativeModel("gemini-1.5-flash")
            elif self._provider == "openai":
                from openai import OpenAI
                if self.settings.openai_api_key:
                    self._client = OpenAI(api_key=self.settings.openai_api_key.get_secret_value())
        except Exception as e:
            logger.warning(f"Failed to init LLM for query understanding: {e}")

    def analyze_query(self, user_message: str, history: List[Dict[str, str]] = None) -> QueryUnderstandingResult:
        if not self.settings.enable_query_rewriting or not self._client:
            return self._fallback(user_message)
            
        history = history or []
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-4:]])
        
        prompt = f"{QUERY_UNDERSTANDING_PROMPT}\n\nRecent History:\n{history_text}\n\nUser Message: {user_message}\n\nRespond strictly with JSON."

        try:
            if self._provider == "gemini":
                response = self._client.generate_content(
                    prompt,
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
                )
                result_text = response.text
            elif self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.1,
                    response_format={ "type": "json_object" }
                )
                result_text = response.choices[0].message.content
            else:
                return self._fallback(user_message)
                
            data = json.loads(result_text)
            
            queries = []
            for sq in data.get("search_queries", []):
                queries.append(SearchQuery(
                    query=sq.get("query", ""),
                    is_keyword=sq.get("is_keyword", False),
                    is_hyde=False
                ))
                
            if not self.settings.enable_multi_query:
                queries = queries[:1]
                
            if not queries:
                queries = [SearchQuery(query=data.get("rewritten_query", user_message))]

            return QueryUnderstandingResult(
                original_query=user_message,
                rewritten_query=data.get("rewritten_query", user_message),
                search_queries=queries,
                medical_terms_normalized=data.get("medical_terms_normalized", {})
            )
            
        except Exception as e:
            logger.error(f"Query understanding failed: {e}")
            return self._fallback(user_message)

    def _fallback(self, user_message: str) -> QueryUnderstandingResult:
        return QueryUnderstandingResult(
            original_query=user_message,
            rewritten_query=user_message,
            search_queries=[SearchQuery(query=user_message)],
            medical_terms_normalized={}
        )

