from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
import enum

from .base import Base

class TrustLevel(str, enum.Enum):
    PRIMARY_MEDICAL_GUIDELINE = "PRIMARY_MEDICAL_GUIDELINE"
    GOVERNMENT_HEALTH = "GOVERNMENT_HEALTH"
    MAJOR_MEDICAL_ORGANIZATION = "MAJOR_MEDICAL_ORGANIZATION"
    PEER_REVIEWED_RESEARCH = "PEER_REVIEWED_RESEARCH"
    REFERENCE_MEDICAL_SOURCE = "REFERENCE_MEDICAL_SOURCE"

class FreshnessStatus(str, enum.Enum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    OUTDATED = "OUTDATED"
    SUPERSEDED = "SUPERSEDED"

class KnowledgeSource(Base):
    """
    Registry of verified medical/health sources.
    """
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    trust_level: Mapped[TrustLevel] = mapped_column(Enum(TrustLevel), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String)
    language: Mapped[str] = mapped_column(String, default="en")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    documents: Mapped[List["KnowledgeDocument"]] = relationship("KnowledgeDocument", back_populates="source")

class KnowledgeDocument(Base):
    """
    A document/article ingested from a KnowledgeSource.
    """
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String)
    domain_topic: Mapped[Optional[str]] = mapped_column(String)  # e.g., MENSTRUAL_HEALTH
    version: Mapped[str] = mapped_column(String, default="v1")
    freshness: Mapped[FreshnessStatus] = mapped_column(Enum(FreshnessStatus), default=FreshnessStatus.CURRENT)
    
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    """
    A chunk of text from a KnowledgeDocument, embedded for vector search.
    """
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(768))  # Gemini uses 768 dimensions
    
    # Metadata for citation and retrieval filtering
    heading: Mapped[Optional[str]] = mapped_column(String)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")
