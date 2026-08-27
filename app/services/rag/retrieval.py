from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.models.rag import DocumentChunk, KnowledgeDocument, KnowledgeSource, TrustLevel
from app.services.rag.embeddings import get_embedding_provider

class Citation(BaseModel):
    source: str
    title: str
    url: Optional[str] = None
    section: Optional[str] = None
    publication_date: Optional[str] = None

class RetrievedEvidence(BaseModel):
    content: str
    confidence: str
    citation: Citation

class MedicalKnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.embed_provider = get_embedding_provider()

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5
    ) -> List[RetrievedEvidence]:
        """
        Retrieves relevant chunks using semantic search (vector).
        In a production environment, this would ideally use hybrid search 
        (vector + pg_trgm/tsvector) combined via Reciprocal Rank Fusion (RRF).
        """
        # 1. Generate Query Embedding
        query_embedding = self.embed_provider.embed_text(query)
        
        # 2. Vector Search (using pgvector L2 distance / cosine distance)
        # We use cosine distance: DocumentChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(DocumentChunk, KnowledgeDocument, KnowledgeSource)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .join(KnowledgeSource, KnowledgeDocument.source_id == KnowledgeSource.id)
            .filter(KnowledgeSource.active == True)
        )
        
        if domain:
            stmt = stmt.filter(KnowledgeDocument.domain_topic == domain)
            
        # Order by cosine distance (closest first)
        stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding)).limit(limit)
        
        results = self.db.execute(stmt).all()
        
        evidence_list = []
        for chunk, doc, source in results:
            # Map TrustLevel to confidence string
            confidence = "HIGH" if source.trust_level in (TrustLevel.PRIMARY_MEDICAL_GUIDELINE, TrustLevel.GOVERNMENT_HEALTH) else "MEDIUM"
            
            citation = Citation(
                source=source.name,
                title=doc.title,
                url=doc.url,
                section=chunk.heading,
                publication_date=doc.publication_date.isoformat() if doc.publication_date else None
            )
            
            evidence_list.append(RetrievedEvidence(
                content=chunk.content,
                confidence=confidence,
                citation=citation
            ))
            
        return evidence_list
