import argparse
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import get_session_factory, init_db
from app.services.llm_manager.manager import LLMProviderManager
from app.services.content_ingestion_service import ContentIngestionService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ingestion_runner")

def main():
    parser = argparse.ArgumentParser(description="Sakhi AI Content Ingestion Runner")
    parser.add_argument("--topic", type=str, required=True, help="Topic slug (e.g. 'periods')")
    parser.add_argument("--limit", type=int, default=1, help="Number of articles to generate")
    parser.add_argument("--languages", type=str, default="en,hi,mr", help="Comma-separated language codes")
    parser.add_argument("--publish", action="store_true", help="Publish the articles immediately")
    parser.add_argument("--dry-run", action="store_true", help="Run the pipeline without inserting to the database")
    
    args = parser.parse_args()
    
    langs = [l.strip() for l in args.languages.split(",")]
    
    logger.info("Initializing Database...")
    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()
    
    logger.info("Initializing LLM Manager...")
    llm_manager = LLMProviderManager(settings)
    
    logger.info("Provider Statuses:")
    statuses = llm_manager.get_provider_status()
    for provider, status in statuses.items():
        logger.info(f"  {provider}: {status}")

    service = ContentIngestionService(db=db, llm_manager=llm_manager)
    
    articles_to_generate = [
        "What Is a Period?",
        # In the future, this list would be generated dynamically or pulled from a queue
    ]
    
    for i, title in enumerate(articles_to_generate[:args.limit]):
        logger.info(f"\n========================================\nSAKHI LLM CONTENT PIPELINE\n========================================")
        logger.info(f"Article {i+1}/{min(args.limit, len(articles_to_generate))}: {title}")
        try:
            results = service.ingest_article(
                topic_slug=args.topic,
                article_title=title,
                languages=langs,
                publish=args.publish,
                dry_run=args.dry_run
            )
            
            if results.get("status") == "skipped":
                logger.info(f"[SKIP] {title}")
                continue
                
            logger.info("Generation successful!")
            logger.info(f"English Provider Used: {results.get('provider_en')}")
            for lang in langs:
                if lang != "en":
                    logger.info(f"{lang.upper()} Provider Used: {results.get(f'provider_{lang}')}")
                    
        except Exception as e:
            logger.error(f"Failed to ingest article '{title}': {e}", exc_info=True)
            
if __name__ == "__main__":
    main()

