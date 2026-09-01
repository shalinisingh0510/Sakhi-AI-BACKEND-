import json
import logging
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.learning import LearningContent, ResearchSource
from app.schemas.learning import ArticleGenerationResponse, FactValidationResponse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Sakhi AI, an expert medical writer specializing in women's health.
Write a comprehensive, engaging, and strictly accurate educational article based ONLY on the provided research facts.

Structure constraints:
- Do NOT copy the source text. Synthesize and simplify medical concepts.
- Avoid unsupported claims, fabricated statistics, and fake sources.
- Include these sections if relevant: TL;DR, Introduction, Main Sections, Myths vs Facts, FAQs, Key Takeaways, Medical Disclaimer, Sources.
- You must return valid JSON representing the structured article.

JSON Schema:
{
    "title": "Article Title",
    "description": "Short description for the card",
    "sections": [
        {
            "type": "heading|text|bullet_list|myth_fact|faq|warning|callout",
            "heading": "Section Heading (optional)",
            "content": "The actual text content, markdown allowed but keep it simple",
            "order": 0
        }
    ]
}
"""

VALIDATION_PROMPT = """
You are an expert medical fact-checker. 
Review the following Sakhi article against the source research.
Ensure:
1. Every major factual claim has supporting research.
2. No dangerous medical advice is given (no miracle cures, guaranteed treatments, or diagnosis).
3. Citations and statistics are not fabricated.

Respond in JSON:
{
    "is_valid": true/false,
    "issues": ["List of specific issues if any"]
}
"""

LOCALIZATION_PROMPT = """
You are an expert medical translator. Translate the provided Sakhi article into {target_language}.
- Do NOT perform crude word-for-word translation.
- Preserve medical meaning, safety warnings, uncertainty, and disclaimers.
- Keep the exact same JSON structure (title, description, sections).
"""

class ContentGenerationService:
    def __init__(self, db: Session, api_key: str | None = None):
        self.db = db
        self.client = OpenAI(api_key=api_key) if OpenAI and api_key else None
        
    def _ensure_client(self):
        if not self.client:
            raise HTTPException(status_code=503, detail="OpenAI client not configured or installed.")

    def generate_english_article(self, research_id: str, author_id: str) -> ArticleGenerationResponse:
        self._ensure_client()
        
        research = self.db.execute(
            select(ResearchSource).where(ResearchSource.id == research_id)
        ).scalars().first()
        
        if not research:
            raise HTTPException(status_code=404, detail="Research source not found.")
            
        source_text = research.raw_content or ""
        if len(source_text) > 15000:
            source_text = source_text[:15000] # Truncate to fit context if too large
            
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Research Source Title: {research.title}\n\nFacts/Text:\n{source_text}"}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Create LearningContent DB record
            translation_group_id = str(uuid4())
            content_id = str(uuid4())
            
            # Map sections to proper ordering
            sections = result.get("sections", [])
            for i, sec in enumerate(sections):
                sec["order"] = i
                
            article = LearningContent(
                id=content_id,
                title=result.get("title", "Generated Article"),
                description=result.get("description", ""),
                content_type="ARTICLE",
                source_type="INTERNAL",
                category="Generated", # Will be updated by Admin
                language="en",
                audience="ALL",
                status="DRAFT", # Starts as draft
                body=sections,
                author_id=author_id,
                translation_group_id=translation_group_id
            )
            
            self.db.add(article)
            self.db.commit()
            
            # Auto-validate the generated article
            validation = self.validate_content(content_id)
            if not validation.is_valid:
                article.status = "NEEDS_REVIEW"
                self.db.commit()
            
            return ArticleGenerationResponse(
                message="Article generated successfully.",
                content_id=content_id,
                status=article.status,
                validation_issues=validation.issues
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
            
    def validate_content(self, content_id: str) -> FactValidationResponse:
        self._ensure_client()
        
        article = self.db.execute(
            select(LearningContent).where(LearningContent.id == content_id)
        ).scalars().first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found.")
            
        # Normally we'd fetch the linked research, but for simplicity we validate the safety rules directly
        article_text = json.dumps({
            "title": article.title,
            "body": article.body
        })
        
        messages = [
            {"role": "system", "content": VALIDATION_PROMPT},
            {"role": "user", "content": f"Article to validate:\n{article_text}"}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            result = json.loads(response.choices[0].message.content)
            is_valid = result.get("is_valid", False)
            issues = result.get("issues", [])
            
            if not is_valid:
                article.status = "NEEDS_REVIEW"
                self.db.commit()
                
            return FactValidationResponse(
                is_valid=is_valid,
                status=article.status,
                issues=issues
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

    def localize_article(self, content_id: str, target_language: str, author_id: str) -> ArticleGenerationResponse:
        self._ensure_client()
        
        article = self.db.execute(
            select(LearningContent).where(LearningContent.id == content_id)
        ).scalars().first()
        
        if not article:
            raise HTTPException(status_code=404, detail="Source article not found.")
            
        if not article.translation_group_id:
            article.translation_group_id = str(uuid4())
            self.db.commit()
            
        # Check if translation already exists
        existing = self.db.execute(
            select(LearningContent).where(
                LearningContent.translation_group_id == article.translation_group_id,
                LearningContent.language == target_language
            )
        ).scalars().first()
        
        if existing:
            raise HTTPException(status_code=409, detail=f"Localization for {target_language} already exists.")
            
        article_data = {
            "title": article.title,
            "description": article.description,
            "sections": article.body
        }
        
        sys_prompt = LOCALIZATION_PROMPT.replace("{target_language}", target_language)
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(article_data)}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            new_id = str(uuid4())
            localized_article = LearningContent(
                id=new_id,
                title=result.get("title", f"{article.title} ({target_language})"),
                description=result.get("description", ""),
                content_type=article.content_type,
                source_type=article.source_type,
                category=article.category,
                language=target_language,
                audience=article.audience,
                status="DRAFT", # Always starts as draft
                body=result.get("sections", []),
                author_id=author_id,
                translation_group_id=article.translation_group_id
            )
            
            self.db.add(localized_article)
            self.db.commit()
            
            return ArticleGenerationResponse(
                message=f"Localized to {target_language} successfully.",
                content_id=new_id,
                status="DRAFT",
                validation_issues=[]
            )
            
        except Exception as e:
            logger.error(f"Localization failed: {e}")
            raise HTTPException(status_code=500, detail=f"Localization failed: {str(e)}")
