import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.rag import KnowledgeSource, KnowledgeDocument, DocumentChunk, FreshnessStatus
from app.services.rag.embeddings import get_embedding_provider

class DocumentChunker:
    """
    Splits text into chunks while attempting to preserve structure.
    """
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Simple paragraph-based chunker. 
        In production, this could use LangChain's RecursiveCharacterTextSplitter.
        """
        chunks = []
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        current_heading = None
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
                
            # Basic markdown heading detection
            if p.startswith(("# ", "## ", "### ")):
                current_heading = p.lstrip("#").strip()
                
            if len(current_chunk) + len(p) > self.chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "heading": current_heading
                })
                # Basic overlap strategy: keep the last paragraph of the previous chunk if it fits
                current_chunk = p
            else:
                current_chunk += "\n\n" + p if current_chunk else p
                
        if current_chunk:
             chunks.append({
                "text": current_chunk,
                "heading": current_heading
             })
             
        return chunks

class KnowledgeIngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.embed_provider = get_embedding_provider()
        self.chunker = DocumentChunker()

    def ingest_document(
        self,
        source_id: str,
        title: str,
        content: str,
        url: Optional[str] = None,
        domain_topic: Optional[str] = None,
        publication_date: Optional[datetime] = None
    ) -> KnowledgeDocument:
        """
        Ingests a raw document, chunks it, embeds it, and stores it in the vector DB.
        """
        # Validate source
        source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        if not source:
            raise ValueError(f"KnowledgeSource {source_id} not found or inactive")
            
        if not source.active:
            raise ValueError(f"KnowledgeSource {source_id} is inactive")

        # Create Document Record
        doc = KnowledgeDocument(
            id=str(uuid.uuid4()),
            source_id=source.id,
            title=title,
            url=url,
            domain_topic=domain_topic or source.domain,
            publication_date=publication_date,
            freshness=FreshnessStatus.CURRENT
        )
        self.db.add(doc)
        self.db.flush() # Get the ID
        
        # Chunk the text
        raw_chunks = self.chunker.chunk_text(content)
        if not raw_chunks:
            self.db.commit()
            return doc
            
        # Generate Embeddings (batch)
        texts_to_embed = [c["text"] for c in raw_chunks]
        embeddings = self.embed_provider.embed_batch(texts_to_embed)
        
        # Create Chunk Records
        for i, (chunk_data, embedding) in enumerate(zip(raw_chunks, embeddings)):
            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data["text"],
                heading=chunk_data["heading"],
                embedding=embedding,
                metadata={
                    "source": source.name,
                    "trust_level": source.trust_level.value,
                    "domain": doc.domain_topic
                }
            )
            self.db.add(db_chunk)
            
        self.db.commit()
        self.db.refresh(doc)
        return doc
