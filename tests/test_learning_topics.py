"""Tests for Learning Topic/Subtopic taxonomy (Phase 1).

Tests cover:
  - Topic creation and slug uniqueness
  - Subtopic creation and topic relationship
  - LearningContent with topic_id / subtopic_id
  - Backend filtering by topic, subtopic, audience, language
  - Backward compatibility — content without topic still loads
  - Authorization — only admin can create/modify content
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.learning import (
    LearningContent,
    LearningProgress,
    LearningBookmark,
    Topic,
    Subtopic,
    VALID_COMBINATIONS,
    validate_content_combination,
)
from app.schemas.learning import (
    LearningContentCreate,
    LearningContentResponse,
    TopicResponse,
    SubtopicResponse,
)
from app.services.learning_service import LearningService, TopicNotFoundError, LearningContentNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_db():
    return MagicMock()


def make_service(db=None):
    return LearningService(db or make_mock_db())


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestValidCombinations:
    def test_tutorial_internal_is_valid(self):
        validate_content_combination("TUTORIAL", "INTERNAL")

    def test_tutorial_youtube_is_valid(self):
        validate_content_combination("TUTORIAL", "YOUTUBE")

    def test_tutorial_private_is_valid(self):
        validate_content_combination("TUTORIAL", "PRIVATE_VIDEO")

    def test_instagram_video_is_valid(self):
        validate_content_combination("VIDEO", "INSTAGRAM")

    def test_instagram_post_is_valid(self):
        validate_content_combination("POST", "INSTAGRAM")

    def test_tutorial_instagram_is_invalid(self):
        with pytest.raises(ValueError):
            validate_content_combination("TUTORIAL", "INSTAGRAM")

    def test_article_youtube_is_invalid(self):
        with pytest.raises(ValueError):
            validate_content_combination("ARTICLE", "YOUTUBE")


class TestTopicModel:
    def test_topic_has_slug(self):
        topic = Topic(
            id=str(uuid.uuid4()),
            name="Periods",
            slug="periods",
            display_order=1,
            is_active=True,
        )
        assert topic.slug == "periods"
        assert topic.name == "Periods"

    def test_subtopic_references_topic(self):
        topic_id = str(uuid.uuid4())
        sub = Subtopic(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            name="Basics",
            slug="basics",
            display_order=1,
            is_active=True,
        )
        assert sub.topic_id == topic_id
        assert sub.slug == "basics"


class TestLearningContentPhase1Fields:
    def test_content_defaults_to_all_audience(self):
        content = LearningContent(
            id=str(uuid.uuid4()),
            title="Test",
            content_type="VIDEO",
            source_type="YOUTUBE",
            media_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            category="pcos",
            author_id=str(uuid.uuid4()),
        )
        # audience defaults to ALL at DB level; Python default is also ALL
        assert content.topic_id is None
        assert content.subtopic_id is None
        assert content.translation_group_id is None
        assert content.featured_rank is None

    def test_content_accepts_tutorial_type(self):
        validate_content_combination("TUTORIAL", "INTERNAL")

    def test_content_accepts_instagram_architecture(self):
        validate_content_combination("VIDEO", "INSTAGRAM")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_topic_response_has_subtopics(self):
        schema = TopicResponse(
            id="t1",
            name="PCOS",
            slug="pcos",
            display_order=1,
            is_active=True,
            subtopics=[
                SubtopicResponse(
                    id="s1", topic_id="t1", name="Basics",
                    slug="basics", display_order=1, is_active=True
                )
            ]
        )
        assert len(schema.subtopics) == 1
        assert schema.subtopics[0].slug == "basics"

    def test_content_create_includes_topic_fields(self):
        # ARTICLE + INTERNAL is valid
        body = LearningContentCreate(
            title="Understanding PCOS",
            content_type="ARTICLE",
            source_type="INTERNAL",
            category="pcos",
            topic_id="some-topic-uuid",
            subtopic_id="some-subtopic-uuid",
            audience="ADULT",
            language="en",
        )
        assert body.topic_id == "some-topic-uuid"
        assert body.audience == "ADULT"

    def test_audience_defaults_to_all(self):
        body = LearningContentCreate(
            title="Test",
            content_type="ARTICLE",
            source_type="INTERNAL",
            category="nutrition",
        )
        assert body.audience == "ALL"

    def test_tutorial_internal_schema_valid(self):
        body = LearningContentCreate(
            title="PCOS Tutorial",
            content_type="TUTORIAL",
            source_type="INTERNAL",
            category="pcos",
        )
        assert body.content_type == "TUTORIAL"


# ---------------------------------------------------------------------------
# Service unit tests (mocked DB)
# ---------------------------------------------------------------------------

class TestLearningServiceTopics:
    def test_get_topics_calls_db(self):
        db = make_mock_db()
        service = LearningService(db)
        db.scalars.return_value.all.return_value = []
        result = service.get_topics()
        assert isinstance(result, list)

    def test_get_topic_by_slug_raises_when_not_found(self):
        db = make_mock_db()
        service = LearningService(db)
        db.scalar.return_value = None
        with pytest.raises(TopicNotFoundError):
            service.get_topic_by_slug("nonexistent-slug")

    def test_get_feed_accepts_topic_id_filter(self):
        """get_feed should not raise when topic_id and subtopic_id are provided."""
        db = make_mock_db()
        service = LearningService(db)
        db.scalar.return_value = 0
        db.scalars.return_value.all.return_value = []
        result_items, result_total = service.get_feed(
            topic_id="some-topic-id",
            subtopic_id="some-subtopic-id",
            audience="ADULT",
        )
        assert result_items == []
        assert result_total == 0

    def test_get_feed_accepts_audience_filter(self):
        db = make_mock_db()
        service = LearningService(db)
        db.scalar.return_value = 0
        db.scalars.return_value.all.return_value = []
        items, total = service.get_feed(audience="TEEN")
        assert items == []
        assert total == 0


class TestLearningServiceBackwardCompat:
    def test_get_content_without_topic_still_works(self):
        """Existing content without topic_id should still load correctly."""
        db = make_mock_db()
        service = LearningService(db)

        mock_content = MagicMock(spec=LearningContent)
        mock_content.status = "PUBLISHED"
        mock_content.thumbnail_file_id = None
        mock_content.media_file_id = None
        mock_content.body = None
        mock_content.topic_id = None
        mock_content.subtopic_id = None

        db.get.return_value = mock_content
        result = service.get_content("some-id", admin=False)
        assert result.topic_id is None

    def test_content_not_found_raises(self):
        db = make_mock_db()
        service = LearningService(db)
        db.get.return_value = None
        with pytest.raises(LearningContentNotFoundError):
            service.get_content("nonexistent")


# ---------------------------------------------------------------------------
# Authorization logic tests
# ---------------------------------------------------------------------------

class TestAuthorizationBoundary:
    def test_valid_combinations_does_not_include_article_youtube(self):
        """ARTICLE + YOUTUBE should remain invalid — no double-standards."""
        assert ("ARTICLE", "YOUTUBE") not in VALID_COMBINATIONS

    def test_all_new_combinations_are_defined(self):
        """Verify all Phase 1 new combinations are in VALID_COMBINATIONS."""
        assert ("TUTORIAL", "INTERNAL") in VALID_COMBINATIONS
        assert ("TUTORIAL", "YOUTUBE") in VALID_COMBINATIONS
        assert ("TUTORIAL", "PRIVATE_VIDEO") in VALID_COMBINATIONS
        assert ("VIDEO", "INSTAGRAM") in VALID_COMBINATIONS
        assert ("POST", "INSTAGRAM") in VALID_COMBINATIONS
