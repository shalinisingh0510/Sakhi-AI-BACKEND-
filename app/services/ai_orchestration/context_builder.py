from typing import List
from app.schemas.knowledge import RetrievedChunk, CompressedEvidence

class ContextBuilder:
    """
    Builds the final LLM prompt context by formatting retrieved chunks
    and compressed evidence into a structured string, keeping system
    instructions and evidence separate.
    """

    @staticmethod
    def build_context(chunks: List[RetrievedChunk], compressed_evidence: List[CompressedEvidence] = None) -> str:
        if not chunks:
            return ""

        context_parts = []
        
        # 1. Add Compressed Evidence (if any)
        if compressed_evidence:
            context_parts.append("### Key Synthesized Facts ###")
            for i, ce in enumerate(compressed_evidence, 1):
                conflict_flag = "[CONFLICT DETECTED]" if ce.is_conflicting else ""
                context_parts.append(f"{i}. {conflict_flag} {ce.statement}")
            context_parts.append("\n")

        # 2. Add Source Documents
        context_parts.append("### Retrieved Medical Evidence ###")
        for i, chunk in enumerate(chunks, 1):
            source_block = f"""[SOURCE_{i}]
Title: {chunk.citation.title}
Organization: {chunk.citation.organization}
Section: {chunk.citation.section or 'General'}
Authority: {chunk.citation.tier.value}
Content:
{chunk.content}
"""
            context_parts.append(source_block)

        return "\n".join(context_parts)

