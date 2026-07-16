from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4
import re

from app.core.config import Settings
from app.schemas.lesson import LessonDetail, LessonSection, LessonSummary
from app.schemas.auth import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGE_SET = {language.lower() for language in SUPPORTED_LANGUAGES}
DEFAULT_LESSON_LANGUAGE = "english"
DEFAULT_LESSON_AUDIENCE = "general"
DEFAULT_LESSON_CATEGORY = "wellbeing"
DEFAULT_LESSON_SUMMARY = "Trusted educational guidance for everyday health topics."


class LessonError(Exception):
    """Base exception for lesson operations."""


class LessonNotFoundError(LessonError):
    pass


class DuplicateLessonSlugError(LessonError):
    pass


class InvalidLessonContentError(LessonError):
    pass


@dataclass(slots=True)
class StoredLesson:
    id: str
    slug: str
    title: str
    category: str
    summary: str
    language: str
    audience: str
    tags: list[str]
    sections: list[dict[str, str]]
    published: bool
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None = None

    def to_summary(self) -> LessonSummary:
        return LessonSummary(
            id=self.id,
            slug=self.slug,
            title=self.title,
            category=self.category,
            language=self.language,
            audience=self.audience,
            published=self.published,
            section_count=len(self.sections),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_detail(self) -> LessonDetail:
        return LessonDetail(
            id=self.id,
            slug=self.slug,
            title=self.title,
            category=self.category,
            language=self.language,
            audience=self.audience,
            published=self.published,
            section_count=len(self.sections),
            created_at=self.created_at,
            updated_at=self.updated_at,
            summary=self.summary,
            tags=self.tags,
            sections=self.sections,
        )


class LessonStoreProtocol(Protocol):
    def create_lesson(
        self,
        *,
        title: str,
        slug: str,
        category: str,
        summary: str,
        language: str,
        audience: str,
        tags: list[str],
        sections: list[dict[str, str]],
        published: bool,
        created_by_user_id: str | None = None,
    ) -> StoredLesson:
        ...

    def get_by_id(self, lesson_id: str) -> StoredLesson | None:
        ...

    def get_by_slug(self, slug: str) -> StoredLesson | None:
        ...

    def list_lessons(self, *, published_only: bool | None = None) -> list[StoredLesson]:
        ...

    def list_categories(self, *, published_only: bool = True) -> list[tuple[str, int]]:
        ...

    def update_lesson(
        self,
        *,
        lesson_id: str,
        title: str | None = None,
        slug: str | None = None,
        category: str | None = None,
        summary: str | None = None,
        language: str | None = None,
        audience: str | None = None,
        tags: list[str] | None = None,
        sections: list[dict[str, str]] | None = None,
        published: bool | None = None,
    ) -> StoredLesson:
        ...

    def delete_lesson(self, lesson_id: str) -> None:
        ...


class LessonService:
    def __init__(self, settings: Settings, store: LessonStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def create_lesson(
        self,
        *,
        title: str,
        slug: str | None,
        category: str,
        summary: str,
        language: str,
        audience: str,
        tags: list[str],
        sections: list[LessonSection],
        published: bool,
        created_by_user_id: str | None = None,
    ) -> StoredLesson:
        normalized_slug = self._normalize_slug(slug or title)
        self._validate_content_sections(sections)
        stored = self._store.create_lesson(
            title=title.strip(),
            slug=normalized_slug,
            category=category.strip().lower(),
            summary=summary.strip(),
            language=language.strip().lower(),
            audience=audience.strip().lower(),
            tags=self._normalize_tags(tags),
            sections=[section.model_dump() for section in sections],
            published=published,
            created_by_user_id=created_by_user_id,
        )
        return stored

    def list_lessons(
        self,
        *,
        category: str | None = None,
        language: str | None = None,
        search: str | None = None,
        published_only: bool = True,
    ) -> list[LessonSummary]:
        lessons = self._store.list_lessons(published_only=published_only)
        normalized_category = category.strip().lower() if category else None
        normalized_language = language.strip().lower() if language else None
        normalized_search = search.strip().lower() if search else None

        filtered: list[StoredLesson] = []
        for lesson in lessons:
            if normalized_category and lesson.category != normalized_category:
                continue
            if normalized_language and lesson.language != normalized_language:
                continue
            if normalized_search and normalized_search not in self._lesson_search_text(lesson):
                continue
            filtered.append(lesson)
        return [lesson.to_summary() for lesson in filtered]

    def get_lesson(self, *, slug: str, published_only: bool = True) -> LessonDetail:
        lesson = self._store.get_by_slug(slug.strip().lower())
        if lesson is None or (published_only and not lesson.published):
            raise LessonNotFoundError("Lesson not found.")
        return lesson.to_detail()

    def get_lesson_by_id(self, lesson_id: str) -> LessonDetail:
        lesson = self._store.get_by_id(lesson_id)
        if lesson is None:
            raise LessonNotFoundError("Lesson not found.")
        return lesson.to_detail()

    def list_categories(self, *, published_only: bool = True) -> list[dict[str, int | str]]:
        return [{"name": category, "lesson_count": count} for category, count in self._store.list_categories(published_only=published_only)]

    def update_lesson(
        self,
        *,
        lesson_id: str,
        title: str | None = None,
        slug: str | None = None,
        category: str | None = None,
        summary: str | None = None,
        language: str | None = None,
        audience: str | None = None,
        tags: list[str] | None = None,
        sections: list[LessonSection] | None = None,
        published: bool | None = None,
    ) -> StoredLesson:
        if sections is not None:
            self._validate_content_sections(sections)
        return self._store.update_lesson(
            lesson_id=lesson_id,
            title=title.strip() if title is not None else None,
            slug=self._normalize_slug(slug) if slug is not None else None,
            category=category.strip().lower() if category is not None else None,
            summary=summary.strip() if summary is not None else None,
            language=language.strip().lower() if language is not None else None,
            audience=audience.strip().lower() if audience is not None else None,
            tags=self._normalize_tags(tags) if tags is not None else None,
            sections=[section.model_dump() for section in sections] if sections is not None else None,
            published=published,
        )

    def delete_lesson(self, *, lesson_id: str) -> None:
        self._store.delete_lesson(lesson_id)

    def _normalize_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        if not slug:
            raise InvalidLessonContentError("Lesson slug cannot be empty.")
        return slug

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized = [tag.strip().lower() for tag in tags if tag.strip()]
        seen: set[str] = set()
        unique_tags: list[str] = []
        for tag in normalized:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        return unique_tags

    def _validate_content_sections(self, sections: list[LessonSection]) -> None:
        if not sections:
            raise InvalidLessonContentError("At least one lesson section is required.")

    def _lesson_search_text(self, lesson: StoredLesson) -> str:
        section_text = " ".join(section["heading"] + " " + section["body"] for section in lesson.sections)
        return " ".join([lesson.title, lesson.category, lesson.summary, lesson.audience, " ".join(lesson.tags), section_text]).lower()
