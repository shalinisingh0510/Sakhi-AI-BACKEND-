import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

HYDE_PROMPT = """
You are an expert women's health medical AI. 
Write a brief, highly relevant, and medically accurate hypothetical document or passage that perfectly answers the user's query.
This hypothetical document will be used ONLY to retrieve similar real evidence from our database.
Do NOT include greetings or meta-commentary. Just write the factual passage.

User Query: {query}
"""

class HyDEService:
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
            logger.warning(f"Failed to init LLM for HyDE: {e}")

    def generate_hypothetical_document(self, query: str) -> str:
        if not self.settings.enable_hyde or not self._client:
            return ""
            
        prompt = HYDE_PROMPT.format(query=query)

        try:
            if self._provider == "gemini":
                response = self._client.generate_content(
                    prompt,
                    generation_config={"temperature": 0.2, "max_output_tokens": 150}
                )
                return response.text.strip()
            elif self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
            else:
                return ""
        except Exception as e:
            logger.error(f"HyDE generation failed: {e}")
            return ""

