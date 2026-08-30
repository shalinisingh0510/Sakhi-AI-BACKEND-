from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.rag import KnowledgeSource, KnowledgeDocument, DocumentChunk, TrustLevel
from app.services.rag.embeddings import MockEmbeddingProvider
from app.services.rag.ingestion import KnowledgeIngestionService, SemanticChunker
from app.services.rag.loaders import DocumentCleaner, DocumentLoader, calculate_content_hash
from app.services.rag.retrieval import MedicalKnowledgeService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    KnowledgeSource.__table__.create(bind=engine, checkfirst=True)
    KnowledgeDocument.__table__.create(bind=engine, checkfirst=True)
    DocumentChunk.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    return Session()


def test_document_cleaner_and_hash():
    raw_text = """# Menstrual Health
Cookie policy: accept all cookies.

The normal menstrual cycle lasts 28 days.

Terms of use apply.
"""
    cleaned = DocumentCleaner.clean(raw_text)
    assert "Cookie policy" not in cleaned
    assert "Terms of use" not in cleaned
    assert "Menstrual Health" in cleaned
    assert "The normal menstrual cycle lasts 28 days." in cleaned

    h1 = calculate_content_hash(cleaned)
    h2 = calculate_content_hash(cleaned)
    assert h1 == h2
    assert len(h1) == 64


def test_semantic_chunker():
    chunker = SemanticChunker(target_chunk_size=150)
    sample_text = """# Section 1
First paragraph explaining PCOS and hormonal changes in detail.

## Section 2
Second paragraph explaining lifestyle intervention and nutrition.
"""
    chunks = chunker.chunk(sample_text)
    assert len(chunks) >= 1
    assert all("heading" in c and "text" in c and "content_hash" in c for c in chunks)


def test_ingestion_and_deduplication():
    db = setup_in_memory_db()
    embed_provider = MockEmbeddingProvider()
    service = KnowledgeIngestionService(db=db, embedding_provider=embed_provider)

    source = service.get_or_create_source(
        name="WHO Health",
        organization="WHO",
        domain="menstrual_health",
        trust_level=TrustLevel.GOVERNMENT_HEALTH,
    )

    doc_content = "# Period Pain\n\nHeat therapy and hydration relieve primary dysmenorrhea cramps."
    doc = service.ingest_document(
        source_id=source.id,
        title="Dysmenorrhea Guide",
        content=doc_content,
        domain_topic="menstrual_health",
        url="https://who.int/dysmenorrhea",
    )

    assert doc.title == "Dysmenorrhea Guide"
    assert len(doc.chunks) > 0

    # Re-ingest with modified content should update rather than duplicate
    updated_doc = service.ingest_document(
        source_id=source.id,
        title="Dysmenorrhea Guide",
        content=doc_content + "\n\nGentle exercise also helps.",
        domain_topic="menstrual_health",
    )

    assert updated_doc.id == doc.id
    db.close()


def test_medical_knowledge_retrieval_and_thresholds():
    db = setup_in_memory_db()
    embed_provider = MockEmbeddingProvider()
    ingestion_service = KnowledgeIngestionService(db=db, embedding_provider=embed_provider)

    # Ingest Menstrual Health Doc
    source1 = ingestion_service.get_or_create_source(
        name="WHO",
        organization="World Health Organization",
        domain="menstrual_health",
    )
    ingestion_service.ingest_document(
        source_id=source1.id,
        title="Menstrual Cramps",
        content="# Menstrual Cramps\n\nHeat therapy and hydration provide evidence-based relief for cramps.",
        domain_topic="menstrual_health",
        url="https://who.int/cramps",
    )

    # Ingest PCOS Doc
    source2 = ingestion_service.get_or_create_source(
        name="ACOG",
        organization="ACOG",
        domain="pcos",
    )
    ingestion_service.ingest_document(
        source_id=source2.id,
        title="PCOS Overview",
        content="# PCOS\n\nPolycystic Ovary Syndrome involves oligo-ovulation, hyperandrogenism, and ultrasound follicles.",
        domain_topic="pcos",
        url="https://acog.org/pcos",
    )

    retrieval_service = MedicalKnowledgeService(
        db=db,
        embedding_provider=embed_provider,
        similarity_threshold=0.0,
    )

    # 1. Relevant query
    result = retrieval_service.search("How to relieve menstrual cramps with heat?")
    assert result.has_sufficient_context is True
    assert result.status == "SUCCESS"
    assert len(result.matched_chunks) > 0
    assert result.matched_chunks[0].citation.source_name in ("WHO", "ACOG")

    # 2. Topic-filtered query
    pcos_result = retrieval_service.search("Rotterdam criteria", topic="pcos")
    assert pcos_result.has_sufficient_context is True
    assert all(c.topic.value == "pcos" for c in pcos_result.matched_chunks)

    # 3. Developer Debug Search
    debug_info = retrieval_service.debug_search("What is PCOS?")
    assert "query" in debug_info
    assert "matches" in debug_info
    assert len(debug_info["matches"]) > 0

    db.close()
