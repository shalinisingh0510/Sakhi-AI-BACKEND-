from typing import List, Optional
from pydantic import BaseModel

class ArticleSection(BaseModel):
    title: str
    content: str

class MythVsFact(BaseModel):
    myth: str
    fact: str

class FAQ(BaseModel):
    question: str
    answer: str

class Source(BaseModel):
    title: str
    url: str
    summary: str

class GeneratedArticle(BaseModel):
    title: str
    short_description: str
    tldr: str
    introduction: str
    sections: List[ArticleSection]
    myths_vs_facts: List[MythVsFact]
    faqs: List[FAQ]
    key_takeaways: List[str]
    medical_disclaimer: str
    sources: List[Source]

class FactValidationResult(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    dangerous_claims_found: bool = False

class GeneratedTranslation(BaseModel):
    title: str
    short_description: str
    tldr: str
    introduction: str
    sections: List[ArticleSection]
    myths_vs_facts: List[MythVsFact]
    faqs: List[FAQ]
    key_takeaways: List[str]
    medical_disclaimer: str

class TranslationValidationResult(BaseModel):
    is_valid: bool
    missing_warnings: bool = False
    changed_medical_meaning: bool = False
    reason: Optional[str] = None

