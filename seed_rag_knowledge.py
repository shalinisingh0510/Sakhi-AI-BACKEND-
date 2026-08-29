import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.db.session import init_db, get_session_factory
from app.core.config import get_settings
from app.services.rag.ingestion import KnowledgeIngestionService
from app.models.rag import TrustLevel

def seed_data():
    settings = get_settings()
    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    try:
        service = KnowledgeIngestionService(db)
        
        print("Creating Source...")
        source = service.get_or_create_source(
            name="Dummy WHO",
            organization="World Health Organization",
            trust_level=TrustLevel.GOVERNMENT_HEALTH
        )
        
        print("Ingesting Document 1: Endometriosis...")
        content1 = """
        # Endometriosis Overview
        Endometriosis is a disease in which tissue similar to the lining of the uterus grows outside the uterus.
        It can cause severe pain in the pelvis and make it harder to get pregnant.
        
        ## Symptoms
        The primary symptom of endometriosis is pelvic pain, often associated with menstrual periods.
        Other symptoms include:
        - Pain during or after sex
        - Pain with bowel movements or urination
        - Excessive bleeding
        - Infertility
        - Fatigue, diarrhea, constipation, bloating or nausea
        """
        service.ingest_document(
            source_id=source.id,
            title="Endometriosis Fact Sheet",
            content=content1,
            domain_topic="menstrual_health",
            url="https://who.int/dummy/endometriosis"
        )
        
        print("Ingesting Document 2: PCOS...")
        content2 = """
        # Polycystic Ovary Syndrome (PCOS)
        PCOS is a common hormonal condition that affects women of reproductive age.
        
        ## Symptoms
        - Irregular periods
        - Excess androgen
        - Polycystic ovaries
        - Weight gain
        - Acne
        
        ## Management
        Lifestyle changes such as a balanced diet and regular exercise are often the first line of treatment.
        """
        service.ingest_document(
            source_id=source.id,
            title="PCOS Fact Sheet",
            content=content2,
            domain_topic="menstrual_health",
            url="https://who.int/dummy/pcos"
        )
        
        print("Successfully seeded dummy RAG data.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()

