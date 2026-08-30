from __future__ import annotations

from pathlib import Path

from app.core.cache import InMemoryCacheBackend
from app.core.config import Settings
from app.db import PostgresAnalyticsStore, PostgresAuthStore, PostgresLessonStore
from app.schemas.auth import SUPPORTED_LANGUAGES
from app.schemas.lesson import LessonSection
from app.services.analytics import AnalyticsService
from app.services.lessons import LessonService


class CountingLessonStore(PostgresLessonStore):
    def __init__(self, pool) -> None:
        super().__init__(pool)
        self.list_lessons_calls = 0
        self.search_lessons_calls = 0
        self.get_categories_calls = 0
        self.get_lesson_calls = 0

    def list_lessons(self, *, published_only: bool | None = None):
        self.list_lessons_calls += 1
        return super().list_lessons(published_only=published_only)

    def search_lessons(self, query: str, *, published_only: bool | None = None):
        self.search_lessons_calls += 1
        return super().search_lessons(query, published_only=published_only)


class CountingAnalyticsStore(PostgresAnalyticsStore):
    def __init__(self, pool) -> None:
        super().__init__(pool)
        self.platform_overview_calls = 0
        self.user_engagement_calls = 0
        self.active_users_calls = 0

    def get_platform_overview(self) -> dict[str, int]:
        self.platform_overview_calls += 1
        return super().get_platform_overview()


REGISTER_USER = {
    "name": "Asha Verma",
    "email": "asha.verma@sakhi.ai",
    "password": "StrongPass123!",
}


def test_lesson_catalog_cache_reuses_reads_until_mutation(tmp_path: Path, test_db_url: str, db_pool_session) -> None:
    settings = Settings(database_url=test_db_url, cache_ttl_seconds=300)
    store = CountingLessonStore(db_pool_session)
    service = LessonService(settings, store=store, cache=InMemoryCacheBackend())

    first = service.list_lessons()
    second = service.list_lessons()

    assert store.list_lessons_calls == 1
    assert [lesson.slug for lesson in first] == [lesson.slug for lesson in second]

    service.create_lesson(
        title="Caching in Practice",
        slug="caching-in-practice",
        category="wellbeing",
        summary="A short lesson that demonstrates cache invalidation.",
        language="english",
        audience="general",
        tags=["cache", "performance"],
        translations=[],
        sections=[LessonSection(heading="Why caching helps", body="It reduces repeated work.")],
        published=True,
        created_by_user_id="fake_user",
    )

    third = service.list_lessons()

    assert store.list_lessons_calls == 2
    assert any(lesson.slug == "caching-in-practice" for lesson in third)


def test_lesson_search_uses_store_search_path_and_cache(tmp_path: Path, test_db_url: str, db_pool_session) -> None:
    settings = Settings(database_url=test_db_url, cache_ttl_seconds=300)
    store = CountingLessonStore(db_pool_session)
    service = LessonService(settings, store=store, cache=InMemoryCacheBackend())

    service.create_lesson(
        title="Night Rest Ritual",
        slug="night-rest-ritual",
        category="wellbeing",
        summary="A simple routine for calmer evenings.",
        language="english",
        audience="general",
        tags=["rest", "sleep"],
        translations=[],
        sections=[LessonSection(heading="Evening wind-down", body="A moonlight pause can help the mind settle.")],
        published=True,
        created_by_user_id="fake_user",
    )

    first = service.list_lessons(search="moonlight")
    second = service.list_lessons(search="moonlight")

    assert store.search_lessons_calls == 1
    assert store.list_lessons_calls == 0
    assert [lesson.slug for lesson in first] == [lesson.slug for lesson in second]
    assert any(lesson.slug == "night-rest-ritual" for lesson in first)


def test_analytics_overview_cache_reuses_reads_until_new_event(tmp_path: Path, test_db_url: str, db_pool_session) -> None:
    settings = Settings(database_url=test_db_url, cache_ttl_seconds=300)
    auth_store = PostgresAuthStore(db_pool_session)
    user = auth_store.create_user(
        name=REGISTER_USER["name"],
        email=REGISTER_USER["email"],
        password=REGISTER_USER["password"],
        role="user",
    )
    store = CountingAnalyticsStore(db_pool_session)
    service = AnalyticsService(settings, store=store, cache=InMemoryCacheBackend())

    first = service.get_platform_overview()
    second = service.get_platform_overview()

    assert store.platform_overview_calls == 1
    assert first.total_events == second.total_events

    service.track_event(user_id=user.id, event_type="login")
    third = service.get_platform_overview()

    assert store.platform_overview_calls == 2
    assert third.total_events == first.total_events + 1

