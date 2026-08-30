from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.rag import (
    DocumentChunk,
    KnowledgeDocument,
    KnowledgeSource,
    TrustLevel,
)
from app.services.rag.ingestion import KnowledgeIngestionService

SOURCE_CONFIGS = {
    "menstrual_health.md": {
        "source_name": "World Health Organization & NHS",
        "organization": "WHO / NHS",
        "domain": "menstrual_health",
        "trust_level": TrustLevel.GOVERNMENT_HEALTH,
        "url": "https://www.who.int/news-room/fact-sheets/detail/menstrual-health",
    },
    "pcos.md": {
        "source_name": "ACOG Clinical Practice Guidelines",
        "organization": "American College of Obstetricians and Gynecologists",
        "domain": "pcos",
        "trust_level": TrustLevel.PRIMARY_MEDICAL_GUIDELINE,
        "url": "https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2018/06/polycystic-ovary-syndrome",
    },
    "pregnancy.md": {
        "source_name": "CDC Reproductive Health & Pregnancy Guidelines",
        "organization": "Centers for Disease Control and Prevention",
        "domain": "pregnancy",
        "trust_level": TrustLevel.GOVERNMENT_HEALTH,
        "url": "https://www.cdc.gov/pregnancy/index.html",
    },
    "menopause.md": {
        "source_name": "The Menopause Society Guidelines",
        "organization": "The Menopause Society",
        "domain": "menopause",
        "trust_level": TrustLevel.PRIMARY_MEDICAL_GUIDELINE,
        "url": "https://www.menopause.org/for-women/menopause-flashes",
    },
    "contraception.md": {
        "source_name": "WHO Family Planning & Contraception Guidelines",
        "organization": "World Health Organization",
        "domain": "contraception",
        "trust_level": TrustLevel.GOVERNMENT_HEALTH,
        "url": "https://www.who.int/news-room/fact-sheets/detail/family-planning-contraception",
    },
    "endometriosis.md": {
        "source_name": "WHO & RCOG Endometriosis Guidelines",
        "organization": "World Health Organization / RCOG",
        "domain": "endometriosis",
        "trust_level": TrustLevel.PRIMARY_MEDICAL_GUIDELINE,
        "url": "https://www.who.int/news-room/fact-sheets/detail/endometriosis",
    },
}


def run_ingestion(data_dir: Path | None = None, db_url: str | None = None) -> None:
    target_dir = data_dir or (ROOT_DIR / "data" / "knowledge_base")
    print(f"[*] Starting Sakhi Knowledge Ingestion")
    print(f"[*] Target Directory: {target_dir}")

    db_connection_url = db_url or os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'knowledge_base.sqlite3'}")
    print(f"[*] Database URL: {db_connection_url}")

    engine = create_engine(db_connection_url)
    KnowledgeSource.__table__.create(bind=engine, checkfirst=True)
    KnowledgeDocument.__table__.create(bind=engine, checkfirst=True)
    DocumentChunk.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    db = Session()

    ingestion_service = KnowledgeIngestionService(db=db)
    md_files = sorted(list(target_dir.glob("*.md")))

    if not md_files:
        print(f"[!] No .md files found in {target_dir}")
        return

    ingested_count = 0
    total_chunks = 0
    for file_path in md_files:
        cfg = SOURCE_CONFIGS.get(
            file_path.name,
            {
                "source_name": f"{file_path.stem} Source",
                "organization": "Sakhi Medical Library",
                "domain": "womens_health",
                "trust_level": TrustLevel.GOVERNMENT_HEALTH,
                "url": None,
            },
        )

        source = ingestion_service.get_or_create_source(
            name=cfg["source_name"],
            organization=cfg["organization"],
            domain=cfg["domain"],
            trust_level=cfg["trust_level"],
        )

        doc = ingestion_service.ingest_file(
            file_path=file_path,
            source_id=source.id,
            topic=cfg["domain"],
            url=cfg.get("url"),
        )
        chunk_count = len(doc.chunks)
        total_chunks += chunk_count
        print(f" [OK] Ingested: {doc.title} ({cfg['domain']}) -> {chunk_count} chunks")
        ingested_count += 1

    db.close()
    print(f"\n[+] Ingestion Summary: {ingested_count} documents, {total_chunks} total chunks indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sakhi AI Knowledge Ingestion CLI")
    parser.add_argument("--data-dir", type=str, help="Path to knowledge base documents directory")
    parser.add_argument("--db-url", type=str, help="Database connection URL")
    args = parser.parse_args()

    dir_path = Path(args.data_dir) if args.data_dir else None
    run_ingestion(data_dir=dir_path, db_url=args.db_url)
