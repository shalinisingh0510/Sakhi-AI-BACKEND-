from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.rag import (
    DocumentChunk,
    FreshnessStatus,
    KnowledgeDocument,
    KnowledgeSource,
    TrustLevel,
)
from app.schemas.knowledge import (
    Citation,
    DomainTopic,
    RetrievalResult,
    RetrievedChunk,
    SourceTier,
    CompressedEvidence,
)
from app.services.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.rag.query_understanding import QueryUnderstandingService
from app.services.rag.hyde import HyDEService
from app.services.rag.conflict_resolution import ConflictResolutionService

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class MedicalKnowledgeService:
    """
    Advanced Retrieval engine for Sakhi AI's trusted women's health knowledge base.
    Features query understanding, multi-query fusion, HyDE, relevance thresholding,
    freshness ranking, context compression and conflict resolution.
    """
    def __init__(
        self,
        db: Session,
        embedding_provider: EmbeddingProvider | None = None,
        default_top_k: int = 4,
        similarity_threshold: float = 0.35,
    ):
        self.db = db
        self.embed_provider = embedding_provider or get_embedding_provider()
        self.default_top_k = default_top_k
        self.similarity_threshold = similarity_threshold
        
        self.settings = get_settings()
        self.query_understanding = QueryUnderstandingService()
        self.hyde = HyDEService()
        self.conflict_resolver = ConflictResolutionService()

    def preprocess_query(self, query: str) -> str:
        """
        Normalizes query while preserving critical clinical and colloquial terms.
        """
        cleaned = query.strip()
        cleaned = re.sub(r"[^\w\s\-\?]", " ", cleaned)
        return " ".join(cleaned.split())

    def search(
        self,
        query: str,
        topic: Optional[str] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        limit: Optional[int] = None, # Alias for top_k for backward compatibility
        history: Optional[List[Dict[str, str]]] = None,
    ) -> RetrievalResult:
        k = limit if limit is not None else (top_k if top_k is not None else self.default_top_k)
        min_thresh = threshold if threshold is not None else self.similarity_threshold
        
        # 1. Query Understanding (Phase 13)
        understanding_result = self.query_understanding.analyze_query(query, history=history)
        search_queries = [sq.query for sq in understanding_result.search_queries]
        
        # 2. HyDE (Phase 13)
        if self.settings.enable_hyde:
            hypothetical_doc = self.hyde.generate_hypothetical_document(understanding_result.rewritten_query)
            if hypothetical_doc:
                search_queries.append(hypothetical_doc)
                
        # 3. Embedding the queries
        query_embeddings = []
        for q in search_queries:
            processed = self.preprocess_query(q)
            if processed:
                query_embeddings.append(self.embed_provider.embed_text(processed))
                
        if not query_embeddings:
            return RetrievalResult(
                query=query,
                matched_chunks=[],
                has_sufficient_context=False,
                status="INSUFFICIENT_CONTEXT",
            )

        # 4. Fetch active knowledge chunks from DB
        stmt = (
            select(DocumentChunk, KnowledgeDocument, KnowledgeSource)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .join(KnowledgeSource, KnowledgeDocument.source_id == KnowledgeSource.id)
            .filter(KnowledgeSource.active.is_(True))
            .filter(KnowledgeDocument.freshness != FreshnessStatus.SUPERSEDED)
        )

        if topic:
            stmt = stmt.filter(KnowledgeDocument.domain_topic == topic)

        candidates = self.db.execute(stmt).all()

        if not candidates:
            return RetrievalResult(
                query=query,
                matched_chunks=[],
                has_sufficient_context=False,
                status="INSUFFICIENT_CONTEXT",
            )

        # 5. Multi-Query Scoring & Fusion
        chunk_scores: Dict[str, RetrievedChunk] = {}
        
        for chunk, doc, source in candidates:
            emb = chunk.embedding
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            elif not isinstance(emb, list):
                emb = list(emb)

            # Get max score across all queries for this chunk
            max_score = 0.0
            for q_emb in query_embeddings:
                score = cosine_similarity(q_emb, emb)
                if score > max_score:
                    max_score = score
                    
            # Freshness & Authority Ranking Adjustments (Phase 13)
            adjusted_score = max_score
            if self.settings.enable_freshness_ranking:
                # Boost Tier 1
                if source.trust_level in (TrustLevel.PRIMARY_MEDICAL_GUIDELINE, TrustLevel.GOVERNMENT_HEALTH):
                    adjusted_score += 0.02
                # Penalize aging docs
                if doc.freshness == FreshnessStatus.AGING:
                    adjusted_score -= 0.02
                elif doc.freshness == FreshnessStatus.OUTDATED:
                    adjusted_score -= 0.05
                    
            if adjusted_score >= min_thresh:
                confidence = "HIGH" if source.trust_level in (TrustLevel.PRIMARY_MEDICAL_GUIDELINE, TrustLevel.GOVERNMENT_HEALTH) and adjusted_score > 0.60 else "MEDIUM"
                
                tier = (
                    SourceTier.TIER_1_PRIMARY_AUTHORITY
                    if source.trust_level in (TrustLevel.PRIMARY_MEDICAL_GUIDELINE, TrustLevel.GOVERNMENT_HEALTH)
                    else SourceTier.TIER_2_TRUSTED_EDUCATIONAL
                )

                citation = Citation(
                    source_name=source.name,
                    organization=source.organization,
                    tier=tier,
                    title=doc.title,
                    url=doc.url,
                    section=chunk.heading,
                    publication_date=doc.publication_date.isoformat() if doc.publication_date else None,
                )

                try:
                    topic_enum = DomainTopic(doc.domain_topic)
                except ValueError:
                    topic_enum = DomainTopic.MENSTRUAL_HEALTH

                chunk_scores[chunk.id] = RetrievedChunk(
                    content=chunk.content,
                    similarity_score=round(adjusted_score, 4),
                    confidence=confidence,
                    citation=citation,
                    topic=topic_enum,
                    chunk_id=chunk.id,
                    document_id=doc.id,
                )

        # 6. Sort by similarity descending and select Top K
        scored_chunks = list(chunk_scores.values())
        scored_chunks.sort(key=lambda x: x.similarity_score, reverse=True)
        top_matches = scored_chunks[:k]

        has_context = len(top_matches) > 0
        
        # 7. Context Compression & Conflict Resolution (Phase 13)
        compressed_evidence = []
        if has_context and self.settings.enable_context_compression:
            compressed_evidence = self.conflict_resolver.compress_and_resolve(top_matches)

        return RetrievalResult(
            query=query,
            matched_chunks=top_matches,
            compressed_evidence=compressed_evidence,
            has_sufficient_context=has_context,
            status="SUCCESS" if has_context else "INSUFFICIENT_CONTEXT",
        )

    def debug_search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Development inspection utility returning full scoring breakdown for developers.
        """
        result = self.search(query=query, top_k=top_k, threshold=0.0)
        return {
            "query": query,
            "processed_query": self.preprocess_query(query),
            "status": result.status,
            "has_sufficient_context": result.has_sufficient_context,
            "matches": [
                {
                    "similarity_score": c.similarity_score,
                    "confidence": c.confidence,
                    "source": c.citation.source_name,
                    "title": c.citation.title,
                    "heading": c.citation.section,
                    "preview": c.content[:200] + "...",
                }
                for c in result.matched_chunks
            ],
            "compressed_evidence": [
                {
                    "statement": c.statement,
                    "is_conflicting": c.is_conflicting
                } for c in result.compressed_evidence
            ]
        }
