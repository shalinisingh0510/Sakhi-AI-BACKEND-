import logging
import uuid
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.services.llm_manager.manager import LLMProviderManager, TaskType
from app.schemas.ingestion import (
    GeneratedArticle,
    GeneratedTranslation,
    FactValidationResult,
    TranslationValidationResult
)
from app.models.learning import LearningContent, Topic, Subtopic

logger = logging.getLogger(__name__)

class ContentIngestionService:
    def __init__(self, db: Session, llm_manager: LLMProviderManager):
        self.db = db
        self.llm_manager = llm_manager

    def ingest_article(self, topic_slug: str, article_title: str, languages: List[str] = ["en", "hi", "mr"], publish: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Runs the content ingestion pipeline."""
        logger.info(f"Starting ingestion pipeline for topic: {topic_slug}, title: {article_title}")
        
        # 1. Topic resolution
        topic = None
        subtopic = None
        if not dry_run:
            topic = self.db.scalar(select(Topic).where(Topic.slug == topic_slug))
            if not topic:
                raise ValueError(f"Topic not found: {topic_slug}")
            subtopic = self.db.scalar(select(Subtopic).where(Subtopic.topic_id == topic.id).limit(1))
        
        # Check idempotency
        if not dry_run and "en" in languages:
            existing = self.db.scalar(select(LearningContent).where(
                LearningContent.title == article_title, 
                LearningContent.language == "en"
            ))
            if existing:
                logger.info(f"[SKIP] Article '{article_title}' already exists.")
                return {"status": "skipped", "reason": "already_exists"}

        # 2. Source Research (Simulated for this phase)
        research_context = self._perform_research(article_title)

        # 3. English Content Generation
        logger.info("Generating English content...")
        english_prompt = (
            f"Write an original, highly authoritative educational article for Sakhi AI about '{article_title}'.\n"
            f"Use the following research as evidence, but DO NOT copy it verbatim.\n\n"
            f"RESEARCH:\n{research_context}\n\n"
            f"IMPORTANT RULES:\n"
            f"- Write ORIGINAL Sakhi content.\n"
            f"- Do NOT reproduce source wording unnecessarily.\n"
            f"- Do NOT invent claims, citations, statistics, or medical organizations.\n"
            f"- Do NOT provide diagnosis or guaranteed treatment outcomes.\n"
            f"- Output strictly as JSON."
        )
        
        eng_response = self.llm_manager.generate_structured(
            system_prompt="You are Sakhi, a medical content writer. You write accurate, safe, and original health articles. Output JSON matching the schema.",
            user_prompt=english_prompt,
            response_model=GeneratedArticle,
            task=TaskType.CONTENT_GENERATION
        )
        
        eng_article = GeneratedArticle.model_validate(eng_response.structured_data)
        
        # 4. Fact Validation
        logger.info("Validating English content facts...")
        val_prompt = (
            f"Review the following article against the provided research.\n"
            f"Article: {json.dumps(eng_response.structured_data)}\n"
            f"Research: {research_context}\n\n"
            f"Check for unsupported claims, contradictions, fabricated citations, dangerous medical advice, or miracle cure claims."
        )
        
        val_response = self.llm_manager.generate_structured(
            system_prompt="You are a medical fact checker. Check the article for accuracy. Output JSON.",
            user_prompt=val_prompt,
            response_model=FactValidationResult,
            task=TaskType.FACT_VALIDATION
        )
        fact_val = FactValidationResult.model_validate(val_response.structured_data)
        
        if not fact_val.is_valid or fact_val.dangerous_claims_found:
            logger.warning(f"Fact validation failed: {fact_val.reason}")
            # In a real system, we might retry or mark for review. Here we mark for review.
            target_status = "NEEDS_REVIEW"
        else:
            target_status = "PUBLISHED" if publish else "DRAFT"

        translation_group_id = str(uuid.uuid4())
        results = {"en": eng_response.structured_data, "fact_validation": fact_val.model_dump(), "provider_en": eng_response.provider_used.value}
        
        if not dry_run:
            eng_record = self._create_db_record(
                article=eng_article,
                language="en",
                status=target_status,
                translation_group_id=translation_group_id,
                topic_id=topic.id if topic else "test-topic",
                subtopic_id=subtopic.id if subtopic else "test-subtopic"
            )
            self.db.add(eng_record)
            self.db.commit()

        # 5. Translations
        for lang in languages:
            if lang == "en":
                continue
            
            logger.info(f"Generating {lang} translation...")
            trans_prompt = (
                f"Translate the following English article into {lang}. "
                f"Preserve all medical meaning, warnings, structure, FAQs, and the medical disclaimer.\n"
                f"Use natural language.\n\n"
                f"Article to translate: {json.dumps(eng_response.structured_data)}"
            )
            
            trans_response = self.llm_manager.generate_structured(
                system_prompt="You are an expert medical translator. Output JSON.",
                user_prompt=trans_prompt,
                response_model=GeneratedTranslation,
                task=TaskType.TRANSLATION
            )
            trans_article = GeneratedTranslation.model_validate(trans_response.structured_data)
            
            # Translation Validation
            logger.info(f"Validating {lang} translation...")
            tval_prompt = (
                f"Compare the English original and the {lang} translation.\n"
                f"Original: {json.dumps(eng_response.structured_data)}\n"
                f"Translation: {json.dumps(trans_response.structured_data)}\n\n"
                f"Are there any missing warnings, changed medical meanings, or invented claims?"
            )
            tval_response = self.llm_manager.generate_structured(
                system_prompt="You are a medical translation validator. Output JSON.",
                user_prompt=tval_prompt,
                response_model=TranslationValidationResult,
                task=TaskType.TRANSLATION_VALIDATION
            )
            tval = TranslationValidationResult.model_validate(tval_response.structured_data)
            
            if not tval.is_valid or tval.missing_warnings or tval.changed_medical_meaning:
                logger.warning(f"Translation validation failed for {lang}: {tval.reason}")
                lang_status = "NEEDS_REVIEW"
            else:
                lang_status = "PUBLISHED" if publish else "DRAFT"
                
            results[lang] = trans_response.structured_data
            results[f"{lang}_validation"] = tval.model_dump()
            results[f"provider_{lang}"] = trans_response.provider_used.value
            
            if not dry_run:
                # Merge sources from English because they are the same
                trans_data = trans_article.model_dump()
                trans_data["sources"] = [s.model_dump() for s in eng_article.sources]
                full_trans = GeneratedArticle.model_validate(trans_data)
                
                lang_record = self._create_db_record(
                    article=full_trans,
                    language=lang,
                    status=lang_status,
                    translation_group_id=translation_group_id,
                    topic_id=topic.id if topic else "test-topic",
                    subtopic_id=subtopic.id if subtopic else "test-subtopic"
                )
                self.db.add(lang_record)
                self.db.commit()

        return results

    def _perform_research(self, title: str) -> str:
        # Mocking research for this phase
        return (
            "A period (menstruation) is normal vaginal bleeding that occurs as part of a woman's monthly cycle. "
            "Every month, the body prepares for pregnancy. If no pregnancy occurs, the uterus sheds its lining. "
            "The menstrual blood is partly blood and partly tissue from inside the uterus. "
            "Periods usually start between age 11 and 14 and continue until menopause at about age 51. "
            "Symptoms can include cramping, bloating, breast tenderness, and mood swings. "
            "Source: MedlinePlus - Menstruation (https://medlineplus.gov/menstruation.html)"
        )

    def _create_db_record(
        self, 
        article: GeneratedArticle, 
        language: str, 
        status: str, 
        translation_group_id: str,
        topic_id: str,
        subtopic_id: str
    ) -> LearningContent:
        body_data = article.model_dump()
        # Remove title and description from body since they are columns
        del body_data["title"]
        del body_data["short_description"]
        
        record = LearningContent(
            title=article.title,
            description=article.short_description,
            content_type="ARTICLE",
            source_type="INTERNAL",
            body=body_data,
            category="health",
            language=language,
            audience="ALL",
            status=status,
            medical_review_status="NOT_REVIEWED",
            translation_group_id=translation_group_id,
            author_id="SYSTEM-AI-INGESTION-1234",
            topic_id=topic_id,
            subtopic_id=subtopic_id,
            is_featured=False,
            is_short_form=False
        )
        return record
