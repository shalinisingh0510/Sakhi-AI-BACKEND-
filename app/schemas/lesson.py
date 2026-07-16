from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGE_SET = {language.lower() for language in SUPPORTED_LANGUAGES}


class LessonSection(BaseModel):
    heading: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=1, max_length=6000)

    @field_validator("heading", "body")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized


class LessonTranslationRequest(BaseModel):
    language: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=2, max_length=120)
    summary: str = Field(min_length=10, max_length=400)
    sections: list[LessonSection] = Field(default_factory=list)

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_SET:
            raise ValueError("Unsupported language.")
        return normalized

    @field_validator("title", "summary")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[LessonSection]) -> list[LessonSection]:
        if not value:
            raise ValueError("At least one lesson section is required.")
        return value


class LessonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    category: str
    language: str
    audience: str
    published: bool
    section_count: int
    available_languages: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class LessonDetail(LessonSummary):
    summary: str
    tags: list[str] = Field(default_factory=list)
    sections: list[LessonSection] = Field(default_factory=list)


class CreateLessonRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    category: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=10, max_length=400)
    language: str = Field(default="english", max_length=32)
    audience: str = Field(default="general", max_length=80)
    tags: list[str] = Field(default_factory=list)
    translations: list[LessonTranslationRequest] = Field(default_factory=list)
    published: bool = True
    sections: list[LessonSection] = Field(default_factory=list)

    @field_validator("title", "category", "summary", "audience")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        return normalized

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_SET:
            raise ValueError("Unsupported language.")
        return normalized

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(tag).strip().lower() for tag in value if str(tag).strip()]
        return []

    @field_validator("translations")
    @classmethod
    def validate_translations(cls, value: list[LessonTranslationRequest]) -> list[LessonTranslationRequest]:
        seen: set[str] = set()
        for translation in value:
            if translation.language in seen:
                raise ValueError("Duplicate lesson translation language.")
            seen.add(translation.language)
        return value

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[LessonSection]) -> list[LessonSection]:
        if not value:
            raise ValueError("At least one lesson section is required.")
        return value


class UpdateLessonRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    summary: str | None = Field(default=None, min_length=10, max_length=400)
    language: str | None = Field(default=None, max_length=32)
    audience: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = None
    translations: list[LessonTranslationRequest] | None = None
    published: bool | None = None
    sections: list[LessonSection] | None = None

    @field_validator("title", "category", "summary", "audience")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be empty.")
        return normalized

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        return normalized

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_SET:
            raise ValueError("Unsupported language.")
        return normalized

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, list):
            normalized = [str(tag).strip().lower() for tag in value if str(tag).strip()]
            return normalized
        return None

    @field_validator("translations")
    @classmethod
    def validate_translations(cls, value: list[LessonTranslationRequest] | None) -> list[LessonTranslationRequest] | None:
        if value is None:
            return None
        seen: set[str] = set()
        for translation in value:
            if translation.language in seen:
                raise ValueError("Duplicate lesson translation language.")
            seen.add(translation.language)
        return value

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[LessonSection] | None) -> list[LessonSection] | None:
        if value is not None and not value:
            raise ValueError("At least one lesson section is required.")
        return value
