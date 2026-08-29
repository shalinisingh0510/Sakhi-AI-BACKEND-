from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceTier(str, enum.Enum):
    """Hierarchy of authority for women's health sources."""
    TIER_1_PRIMARY_AUTHORITY = "TIER_1_PRIMARY_AUTHORITY"      # WHO, CDC, NHS, ACOG, Ministry of Health
    TIER_2_TRUSTED_EDUCATIONAL = "TIER_2_TRUSTED_EDUCATIONAL"  # Mayo Clinic, Cleveland Clinic, Universities
    TIER_3_COMMUNITY_ANECDOTAL = "TIER_3_COMMUNITY_ANECDOTAL"  # Lived experiences (strictly separated from clinical facts)


class DomainTopic(str, enum.Enum):
    """Extensible taxonomy of women's health knowledge domains."""
    MENSTRUAL_HEALTH = "menstrual_health"
    PCOS = "pcos"
    ENDOMETRIOSIS = "endometriosis"
    PREGNANCY = "pregnancy"
    FERTILITY = "fertility"
    CONTRACEPTION = "contraception"
    MENOPAUSE = "menopause"
    POSTPARTUM = "postpartum"
    BREAST_HEALTH = "breast_health"
    SEXUAL_HEALTH = "sexual_health"
    VAGINAL_HEALTH = "vaginal_health"
    URINARY_HEALTH = "urinary_health"
    NUTRITION = "nutrition"
    MATERNAL_HEALTH = "maternal_health"


class FreshnessStatus(str, enum.Enum):
    CURRENT = "CURRENT"
    AGING = "AGING"
    OUTDATED = "OUTDATED"
    SUPERSEDED = "SUPERSEDED"


class DocumentMetadata(BaseModel):
    """Complete provenance and source metadata for knowledge documents."""
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    title: str
    source_name: str
    organization: str
    tier: SourceTier
    topic: DomainTopic
    condition: Optional[str] = None
    language: str = "en"
    country: Optional[str] = None
    url: Optional[str] = None
    version: str = "v1.0"
    content_hash: str
    publication_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class ChunkMetadata(BaseModel):
    """Metadata retained on individual text chunks for citation and retrieval."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    chunk_index: int
    heading: Optional[str] = None
    source_name: str
    organization: str
    tier: SourceTier
    topic: DomainTopic
    language: str = "en"
    url: Optional[str] = None
    content_hash: str


class Citation(BaseModel):
    """Structured citation returned with retrieved evidence."""
    source_name: str
    organization: str
    tier: SourceTier
    title: str
    url: Optional[str] = None
    section: Optional[str] = None
    publication_date: Optional[str] = None


class RetrievedChunk(BaseModel):
    """A retrieved knowledge chunk with confidence and similarity score."""
    content: str
    similarity_score: float
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    citation: Citation
    topic: DomainTopic
    chunk_id: str
    document_id: str


class RetrievalResult(BaseModel):
    """Full result of knowledge retrieval for a user query."""
    query: str
    matched_chunks: List[RetrievedChunk] = Field(default_factory=list)
    has_sufficient_context: bool = True
    status: str = "SUCCESS"  # "SUCCESS", "INSUFFICIENT_CONTEXT", "OUT_OF_SCOPE"
