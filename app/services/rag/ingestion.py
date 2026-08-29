from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.rag import (
    DocumentChunk,
    FreshnessStatus,
    KnowledgeDocument,
    KnowledgeSource,
    TrustLevel,
)
from app.schemas.knowledge import DomainTopic, SourceTier
from app.services.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.rag.loaders import DocumentCleaner, DocumentLoader, calculate_content_hash

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Splits text into semantically coherent chunks by headings and paragraph boundaries,
    preserving structural hierarchy and metadata context for retrieval.
    """
    def __init__(self, target_chunk_size: int = 800, overlap: int = 100):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk_parts = []
        current_heading = "General"
        current_length = 0

        for p in paragraphs:
            p_strip = p.strip()
            if not p_strip:
                continue

            # Detect markdown headings
            if p_strip.startswith(("# ", "## ", "### ", "#### ")):
                current_heading = p_strip.lstrip("#").strip()

            p_len = len(p_strip)
            if current_length + p_len > self.target_chunk_size and current_chunk_parts:
                chunk_text = "\n\n".join(current_chunk_parts)
                chunks.append({
                    "text": chunk_text,
                    "heading": current_heading,
                    "content_hash": calculate_content_hash(chunk_text),
                })
                current_chunk_parts = [p_strip]
                current_length = p_len
            else:
                current_chunk_parts.append(p_strip)
                current_length += p_len

        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            chunks.append({
                "text": chunk_text,
                "heading": current_heading,
                "content_hash": calculate_content_hash(chunk_text),
            })

        return chunks


class KnowledgeIngestionService:
    """
    Orchestrates document loading, cleaning, deduplication, chunking,
    embedding generation, and vector persistence.
    """
    def __init__(self, db: Session, embedding_provider: EmbeddingProvider | None = None):
        self.db = db
        self.embed_provider = embedding_provider or get_embedding_provider()
        self.chunker = SemanticChunker()

    def get_or_create_source(
        self,
        *,
        name: str,
        organization: str,
        domain: str = "womens_health",
        trust_level: TrustLevel = TrustLevel.GOVERNMENT_HEALTH,
        country: str = "International",
        language: str = "en",
    ) -> KnowledgeSource:
        source = (
            self.db.query(KnowledgeSource)
            .filter(KnowledgeSource.name == name, KnowledgeSource.organization == organization)
            .first()
        )
        if not source:
            source = KnowledgeSource(
                id=str(uuid.uuid4()),
                name=name,
                organization=organization,
                domain=domain,
                trust_level=trust_level,
                country=country,
                language=language,
                active=True,
                last_verified=datetime.utcnow(),
            )
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
        return source

    def ingest_document(
        self,
        *,
        source_id: str,
        title: str,
        content: str,
        url: Optional[str] = None,
        domain_topic: str = "menstrual_health",
        publication_date: Optional[datetime] = None,
        version: str = "v1.0",
    ) -> KnowledgeDocument:
        cleaned_content = DocumentCleaner.clean(content)
        doc_hash = calculate_content_hash(cleaned_content)

        # 1. Deduplication check
        existing_doc = (
            self.db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.source_id == source_id, KnowledgeDocument.title == title)
            .first()
        )

        if existing_doc:
            logger.info(f"Updating existing document: {title}")
            existing_doc.freshness = FreshnessStatus.CURRENT
            existing_doc.url = url
            existing_doc.domain_topic = domain_topic
            existing_doc.version = version
            doc = existing_doc
            # Remove old chunks before re-indexing
            self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        else:
            doc = KnowledgeDocument(
                id=str(uuid.uuid4()),
                source_id=source_id,
                title=title,
                url=url,
                domain_topic=domain_topic,
                version=version,
                freshness=FreshnessStatus.CURRENT,
                publication_date=publication_date or datetime.utcnow(),
            )
            self.db.add(doc)
            self.db.flush()

        # 2. Semantic Chunking
        raw_chunks = self.chunker.chunk(cleaned_content)
        if not raw_chunks:
            self.db.commit()
            return doc

        # 3. Batch Embeddings
        texts_to_embed = [c["text"] for c in raw_chunks]
        embeddings = self.embed_provider.embed_batch(texts_to_embed)

        # 4. Store Chunks with metadata
        source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        source_name = source.name if source else "Unknown Source"
        trust_val = source.trust_level.value if source else "GOVERNMENT_HEALTH"

        for i, (chunk_data, embedding) in enumerate(zip(raw_chunks, embeddings)):
            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data["text"],
                heading=chunk_data.get("heading"),
                embedding=embedding,
                chunk_metadata={
                    "source": source_name,
                    "trust_level": trust_val,
                    "domain": doc.domain_topic,
                    "content_hash": chunk_data.get("content_hash"),
                },
            )
            self.db.add(db_chunk)

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def ingest_file(
        self,
        file_path: Path,
        source_id: str,
        topic: str = "menstrual_health",
        url: Optional[str] = None,
    ) -> KnowledgeDocument:
        loaded = DocumentLoader.load_file(file_path)
        title = file_path.stem.replace("_", " ").title()
        return self.ingest_document(
            source_id=source_id,
            title=title,
            content=loaded["cleaned_content"],
            url=url,
            domain_topic=topic,
        )
