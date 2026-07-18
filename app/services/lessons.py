from __future__ import annotations

from dataclasses import dataclass
import json
import re
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.core.cache import CacheBackendProtocol, build_cache_key
from app.core.config import Settings
from app.schemas.auth import SUPPORTED_LANGUAGES
from app.schemas.lesson import LessonDetail, LessonSection, LessonSummary, LessonTranslationRequest

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
    translations: dict[str, dict[str, object]]
    published: bool
    created_at: object
    updated_at: object
    created_by_user_id: str | None = None

    def available_languages(self) -> list[str]:
        languages = {self.language, *self.translations.keys()}
        return sorted(language for language in languages if language)

    def _resolve_content(self, preferred_language: str | None = None) -> tuple[str, str, list[dict[str, str]], str]:
        normalized_language = preferred_language.strip().lower() if preferred_language else self.language
        if normalized_language == self.language:
            return self.title, self.summary, self.sections, self.language

        translation = self.translations.get(normalized_language)
        if translation is None:
            return self.title, self.summary, self.sections, self.language

        return (
            str(translation["title"]),
            str(translation["summary"]),
            [dict(section) for section in translation["sections"]],
            normalized_language,
        )

    def to_summary(self, preferred_language: str | None = None) -> LessonSummary:
        title, _, sections, resolved_language = self._resolve_content(preferred_language)
        return LessonSummary(
            id=self.id,
            slug=self.slug,
            title=title,
            category=self.category,
            language=resolved_language,
            audience=self.audience,
            published=self.published,
            section_count=len(sections),
            available_languages=self.available_languages(),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_detail(self, preferred_language: str | None = None) -> LessonDetail:
        title, summary, sections, resolved_language = self._resolve_content(preferred_language)
        return LessonDetail(
            id=self.id,
            slug=self.slug,
            title=title,
            category=self.category,
            language=resolved_language,
            audience=self.audience,
            published=self.published,
            section_count=len(sections),
            available_languages=self.available_languages(),
            created_at=self.created_at,
            updated_at=self.updated_at,
            summary=summary,
            tags=self.tags,
            sections=sections,
        )

    def search_text(self) -> str:
        translation_bits: list[str] = []
        for translation in self.translations.values():
            translation_bits.extend(
                [
                    str(translation.get("title", "")),
                    str(translation.get("summary", "")),
                    " ".join(
                        f"{section.get('heading', '')} {section.get('body', '')}"
                        for section in translation.get("sections", [])
                        if isinstance(section, dict)
                    ),
                ]
            )

        section_text = " ".join(section["heading"] + " " + section["body"] for section in self.sections)
        return " ".join(
            [
                self.title,
                self.category,
                self.summary,
                self.audience,
                " ".join(self.tags),
                section_text,
                " ".join(translation_bits),
            ]
        ).lower()


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
        translations: dict[str, dict[str, object]],
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

    def search_lessons(self, query: str, *, published_only: bool | None = None) -> list[StoredLesson]:
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
        translations: dict[str, dict[str, object]] | None = None,
        published: bool | None = None,
    ) -> StoredLesson:
        ...

    def delete_lesson(self, lesson_id: str) -> None:
        ...


class LessonService:
    def __init__(self, settings: Settings, store: LessonStoreProtocol, cache: CacheBackendProtocol | None = None) -> None:
        self._settings = settings
        self._store = store
        self._cache = cache
        self._cache_namespace = "lessons"
        self._cache_ttl = settings.cache_ttl_seconds

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
        translations: list[LessonTranslationRequest],
        sections: list[LessonSection],
        published: bool,
        created_by_user_id: str | None = None,
    ) -> StoredLesson:
        normalized_slug = self._normalize_slug(slug or title)
        normalized_language = self._normalize_language(language)
        self._validate_content_sections(sections)
        normalized_translations = self._normalize_translations(translations, base_language=normalized_language)
        stored = self._store.create_lesson(
            title=title.strip(),
            slug=normalized_slug,
            category=category.strip().lower(),
            summary=summary.strip(),
            language=normalized_language,
            audience=audience.strip().lower(),
            tags=self._normalize_tags(tags),
            sections=[section.model_dump() for section in sections],
            translations=normalized_translations,
            published=published,
            created_by_user_id=created_by_user_id,
        )
        self._invalidate_cache()
        return stored

    def list_lessons(
        self,
        *,
        category: str | None = None,
        language: str | None = None,
        search: str | None = None,
        tag: str | None = None,
        content_language: str | None = None,
        published_only: bool = True,
    ) -> list[LessonSummary]:
        normalized_category = category.strip().lower() if category else None
        normalized_language = self._normalize_language(language) if language else None
        normalized_content_language = self._normalize_language(content_language) if content_language else None
        normalized_search = search.strip().lower() if search else None
        normalized_tag = tag.strip().lower() if tag else None
        cache_key = build_cache_key(
            self._cache_namespace,
            self._cache_version(),
            "list_lessons",
            normalized_category,
            normalized_language,
            normalized_search,
            normalized_tag,
            normalized_content_language,
            published_only,
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return [LessonSummary.model_validate(item) for item in cached]

        if normalized_search:
            lessons = self._store.search_lessons(normalized_search, published_only=published_only)
        else:
            lessons = self._store.list_lessons(published_only=published_only)

        filtered: list[StoredLesson] = []
        for lesson in lessons:
            if normalized_category and lesson.category != normalized_category:
                continue
            if normalized_language and lesson.language != normalized_language:
                continue
            if normalized_tag and normalized_tag not in lesson.tags:
                continue
            filtered.append(lesson)
        result = [lesson.to_summary(normalized_content_language) for lesson in filtered]
        self._cache_set(cache_key, [lesson.model_dump(mode="json") for lesson in result])
        return result

    def get_lesson(self, *, slug: str, content_language: str | None = None, published_only: bool = True) -> LessonDetail:
        normalized_slug = slug.strip().lower()
        normalized_content_language = self._normalize_language(content_language) if content_language else None
        cache_key = build_cache_key(
            self._cache_namespace,
            self._cache_version(),
            "get_lesson",
            normalized_slug,
            normalized_content_language,
            published_only,
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return LessonDetail.model_validate(cached)

        lesson = self._store.get_by_slug(normalized_slug)
        if lesson is None or (published_only and not lesson.published):
            raise LessonNotFoundError("Lesson not found.")
        detail = lesson.to_detail(normalized_content_language)
        self._cache_set(cache_key, detail.model_dump(mode="json"))
        return detail

    def get_lesson_by_id(self, lesson_id: str, *, content_language: str | None = None) -> LessonDetail:
        normalized_content_language = self._normalize_language(content_language) if content_language else None
        cache_key = build_cache_key(
            self._cache_namespace,
            self._cache_version(),
            "get_lesson_by_id",
            lesson_id,
            normalized_content_language,
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return LessonDetail.model_validate(cached)

        lesson = self._store.get_by_id(lesson_id)
        if lesson is None:
            raise LessonNotFoundError("Lesson not found.")
        detail = lesson.to_detail(normalized_content_language)
        self._cache_set(cache_key, detail.model_dump(mode="json"))
        return detail

    def list_categories(self, *, published_only: bool = True) -> list[dict[str, int | str]]:
        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "list_categories", published_only)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return list(cached)
        categories = [{"name": category, "lesson_count": count} for category, count in self._store.list_categories(published_only=published_only)]
        self._cache_set(cache_key, categories)
        return categories

    def list_tags(self, *, published_only: bool = True) -> list[dict[str, int | str]]:
        """Return all unique tags with usage counts, sorted by count descending."""
        from collections import Counter

        cache_key = build_cache_key(self._cache_namespace, self._cache_version(), "list_tags", published_only)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return list(cached)

        lessons = self._store.list_lessons(published_only=published_only)
        counter: Counter[str] = Counter()
        for lesson in lessons:
            for tag in lesson.tags:
                if tag:
                    counter[tag] += 1
        tags = [{"name": tag, "lesson_count": count} for tag, count in counter.most_common()]
        self._cache_set(cache_key, tags)
        return tags

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
        translations: list[LessonTranslationRequest] | None = None,
        sections: list[LessonSection] | None = None,
        published: bool | None = None,
    ) -> StoredLesson:
        if sections is not None:
            self._validate_content_sections(sections)

        normalized_language = self._normalize_language(language) if language is not None else None
        existing_lesson = self._store.get_by_id(lesson_id) if translations is not None else None
        base_language = normalized_language or (existing_lesson.language if existing_lesson is not None else None)
        normalized_translations = (
            self._normalize_translations(translations, base_language=base_language)
            if translations is not None
            else None
        )
        stored = self._store.update_lesson(
            lesson_id=lesson_id,
            title=title.strip() if title is not None else None,
            slug=self._normalize_slug(slug) if slug is not None else None,
            category=category.strip().lower() if category is not None else None,
            summary=summary.strip() if summary is not None else None,
            language=normalized_language,
            audience=audience.strip().lower() if audience is not None else None,
            tags=self._normalize_tags(tags) if tags is not None else None,
            sections=[section.model_dump() for section in sections] if sections is not None else None,
            translations=normalized_translations,
            published=published,
        )
        self._invalidate_cache()
        return stored

    def delete_lesson(self, *, lesson_id: str) -> None:
        self._store.delete_lesson(lesson_id)
        self._invalidate_cache()

    def _cache_version(self) -> int:
        if self._cache is None:
            return 0
        return self._cache.get_version(self._cache_namespace)

    def _cache_get(self, cache_key: str):
        if self._cache is None:
            return None
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        return json.loads(cached)

    def _cache_set(self, cache_key: str, value: object) -> None:
        if self._cache is None:
            return
        self._cache.set(
            cache_key,
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str),
            ttl_seconds=self._cache_ttl,
        )

    def _invalidate_cache(self) -> None:
        if self._cache is not None:
            self._cache.bump_version(self._cache_namespace)

    def _normalize_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        if not slug:
            raise InvalidLessonContentError("Lesson slug cannot be empty.")
        return slug

    def _normalize_language(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_SET:
            raise InvalidLessonContentError("Unsupported language.")
        return normalized

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized = [tag.strip().lower() for tag in tags if tag.strip()]
        seen: set[str] = set()
        unique_tags: list[str] = []
        for tag in normalized:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        return unique_tags

    def _normalize_translations(
        self,
        translations: list[LessonTranslationRequest],
        *,
        base_language: str | None,
    ) -> dict[str, dict[str, object]]:
        normalized: dict[str, dict[str, object]] = {}
        for translation in translations:
            if base_language and translation.language == base_language:
                raise InvalidLessonContentError("Translation language must be different from the base lesson language.")
            if translation.language in normalized:
                raise InvalidLessonContentError("Duplicate lesson translation language.")
            normalized[translation.language] = {
                "title": translation.title.strip(),
                "summary": translation.summary.strip(),
                "sections": [section.model_dump() for section in translation.sections],
            }
        return normalized

    def _validate_content_sections(self, sections: list[LessonSection]) -> None:
        if not sections:
            raise InvalidLessonContentError("At least one lesson section is required.")

    def _lesson_search_text(self, lesson: StoredLesson) -> str:
        return lesson.search_text()

