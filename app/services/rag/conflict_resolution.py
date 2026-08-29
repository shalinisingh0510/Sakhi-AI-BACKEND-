import json
import logging
from typing import List
from datetime import datetime

from app.core.config import get_settings
from app.schemas.knowledge import CompressedEvidence, RetrievedChunk, Citation, SourceTier

logger = logging.getLogger(__name__)

COMPRESSION_PROMPT = """
You are a medical evidence distillation module.
Your task is to analyze a list of retrieved medical evidence chunks, compress them by removing redundancy, and detect any conflicts between sources.

INPUT:
A JSON list of evidence chunks. Each has a 'chunk_id', 'content', 'source_tier', 'publication_date'.

RULES:
1. Distill the information into distinct, non-redundant medical statements.
2. For each statement, list the 'chunk_id's that support it so we can trace provenance.
3. If two sources explicitly disagree on a fact (e.g., A says X is safe, B says X is harmful), create a single statement noting the conflict, set 'is_conflicting' to true, and explain it in 'conflict_note'. 
4. When resolving conflicts, stronger evidence (Tier 1 > Tier 2) or newer dates should be noted.
5. NEVER fabricate consensus if sources disagree.
6. Output MUST be valid JSON matching the schema.

JSON SCHEMA:
{
  "compressed_evidence": [
    {
      "statement": "Clear medical fact",
      "supporting_chunk_ids": ["chunk_id_1"],
      "is_conflicting": false,
      "conflict_note": null
    }
  ]
}
"""

class ConflictResolutionService:
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
            logger.warning(f"Failed to init LLM for conflict resolution: {e}")

    def compress_and_resolve(self, chunks: List[RetrievedChunk]) -> List[CompressedEvidence]:
        if not self.settings.enable_context_compression or not self._client or len(chunks) == 0:
            return self._passthrough(chunks)
            
        chunks_data = []
        for c in chunks:
            chunks_data.append({
                "chunk_id": c.chunk_id,
                "content": c.content,
                "source_tier": c.citation.tier.value,
                "publication_date": c.citation.publication_date
            })
            
        prompt = f"{COMPRESSION_PROMPT}\n\nINPUT CHUNKS:\n{json.dumps(chunks_data, indent=2)}\n\nRespond strictly with JSON."

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
                return self._passthrough(chunks)
                
            data = json.loads(result_text)
            
            chunk_map = {c.chunk_id: c for c in chunks}
            
            results = []
            for item in data.get("compressed_evidence", []):
                supported_ids = item.get("supporting_chunk_ids", [])
                citations = []
                for cid in supported_ids:
                    if cid in chunk_map:
                        citations.append(chunk_map[cid].citation)
                
                # De-duplicate citations
                unique_cites = {c.url or c.title: c for c in citations}.values()
                
                if not unique_cites:
                    continue # Skip if no valid provenance
                    
                results.append(CompressedEvidence(
                    statement=item.get("statement", ""),
                    citations=list(unique_cites),
                    is_conflicting=item.get("is_conflicting", False),
                    conflict_note=item.get("conflict_note")
                ))
                
            if not results:
                return self._passthrough(chunks)
                
            return results
            
        except Exception as e:
            logger.error(f"Context compression failed: {e}")
            return self._passthrough(chunks)

    def _passthrough(self, chunks: List[RetrievedChunk]) -> List[CompressedEvidence]:
        results = []
        for c in chunks:
            results.append(CompressedEvidence(
                statement=c.content,
                citations=[c.citation],
                is_conflicting=False,
                conflict_note=None
            ))
        return results

