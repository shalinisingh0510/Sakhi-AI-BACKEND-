"""Learning Content System models for Sakhi AI.

LearningContent supports:
  - VIDEO  (source: YOUTUBE, PRIVATE_VIDEO)
  - ARTICLE (source: INTERNAL)
  - POST    (source: INTERNAL)
  - TUTORIAL (source: INTERNAL, YOUTUBE, PRIVATE_VIDEO)

Topic / Subtopic taxonomy enables proper content organisation.
Private media assets reference the existing media_files table (psycopg-based, not Alembic-managed).
Thumbnails also reference media_files.

Architecture notes:
  - INSTAGRAM source type is defined here for future extensibility; no import logic yet.
  - translation_group_id allows grouping same content across languages for i18n.
  - audience supports Teen (13-17) / Adult (18+) / All audience filtering.
  - review_status is forward-compatible with the future doctor/medical review workflow.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Index, String, Text, Integer, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text

from app.db.base import Base

# ---------------------------------------------------------------------------
# Valid content-type / source-type combinations
# ---------------------------------------------------------------------------
VALID_COMBINATIONS: frozenset[tuple[str, str]] = frozenset(
    [
        ("VIDEO", "YOUTUBE"),
        ("VIDEO", "PRIVATE_VIDEO"),
        ("ARTICLE", "INTERNAL"),
        ("POST", "INTERNAL"),
        # Phase 1 additions
        ("TUTORIAL", "INTERNAL"),
        ("TUTORIAL", "YOUTUBE"),
        ("TUTORIAL", "PRIVATE_VIDEO"),
        # Instagram architecture — no import logic yet
        ("VIDEO", "INSTAGRAM"),
        ("POST", "INSTAGRAM"),
    ]
)

YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_\-]{11})"
)


def extract_youtube_id(url: str) -> str | None:
    m = YOUTUBE_PATTERN.search(url)
    return m.group(1) if m else None


def validate_content_combination(content_type: str, source_type: str) -> None:
    """Raise ValueError if the combination is not allowed."""
    if (content_type, source_type) not in VALID_COMBINATIONS:
        raise ValueError(
            f"Invalid combination: content_type='{content_type}' with source_type='{source_type}'. "
            f"Valid pairs: {VALID_COMBINATIONS}"
        )


# ---------------------------------------------------------------------------
# Topic taxonomy
# ---------------------------------------------------------------------------

class Topic(Base):
    """A top-level health topic (e.g. Periods, PCOS, Pregnancy)."""
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)  # emoji
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    # Relationships
    subtopics: Mapped[list["Subtopic"]] = relationship(
        "Subtopic", back_populates="topic", cascade="all, delete-orphan",
        order_by="Subtopic.display_order"
    )

    __table_args__ = (
        Index("ix_topics_slug", "slug"),
        Index("ix_topics_is_active", "is_active"),
    )


class Subtopic(Base):
    """A subtopic within a Topic (e.g. Periods → Menstrual Hygiene)."""
    __tablename__ = "subtopics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="subtopics")

    __table_args__ = (
        Index("ix_subtopics_topic_id", "topic_id"),
        Index("ix_subtopics_slug", "slug"),
        UniqueConstraint("topic_id", "slug", name="uq_subtopic_topic_slug"),
    )


# ---------------------------------------------------------------------------
# Learning Content
# ---------------------------------------------------------------------------

class LearningContent(Base):
    __tablename__ = "learning_content"
    __allow_unmapped__ = True

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # VIDEO, ARTICLE, POST, TUTORIAL
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # YOUTUBE, PRIVATE_VIDEO, INTERNAL, INSTAGRAM (architecture only)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # For YOUTUBE: the full URL (e.g. https://www.youtube.com/watch?v=XXXXX)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # For PRIVATE_VIDEO: references media_files.id (psycopg-managed, NOT Alembic FK)
    media_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Thumbnail: also references media_files.id
    thumbnail_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Structured JSON body for ARTICLE / POST / TUTORIAL content blocks
    body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Content classification — category is kept for backward compatibility
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")

    # Phase 1: Topic taxonomy (nullable for backward compatibility)
    topic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    subtopic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("subtopics.id", ondelete="SET NULL"), nullable=True
    )

    # Phase 1: Audience
    # ALL = all users, TEEN = 13-17, ADULT = 18+
    audience: Mapped[str] = mapped_column(
        String(10), default="ALL", server_default="ALL", nullable=False
    )

    # Phase 1: Featured rank (lower = more prominent, NULL = not featured)
    featured_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Phase 1: Translation group — groups same content across languages
    # e.g. English, Hindi, Marathi versions of the same article share a group ID
    translation_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Authorship — references users table id (not FK-constrained)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Status: DRAFT | PUBLISHED | ARCHIVED | UNDER_REVIEW | MEDICALLY_REVIEWED | NEEDS_REVIEW
    # Forward-compatible with doctor/medical review workflow (Phase N)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)

    # Optional extras
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_short_form: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Transient attributes for resolved URLs (not DB columns)
    thumbnail_url: str | None = None
    media_file_url: str | None = None

    __table_args__ = (
        Index("ix_learning_content_status", "status"),
        Index("ix_learning_content_category", "category"),
        Index("ix_learning_content_content_type", "content_type"),
        Index("ix_learning_content_created_at", "created_at"),
        # Phase 1 indexes
        Index("ix_learning_content_topic_id", "topic_id"),
        Index("ix_learning_content_subtopic_id", "subtopic_id"),
        Index("ix_learning_content_language", "language"),
        Index("ix_learning_content_audience", "audience"),
        Index("ix_learning_content_published_at", "published_at"),
    )


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_content.id", ondelete="CASCADE"),
        primary_key=True,
    )

    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # For VIDEO: seconds watched; for ARTICLE: 0 or 100 (started/completed)
    watch_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0-100 progress percentage
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_learning_progress_user_id", "user_id"),
    )


class LearningBookmark(Base):
    __tablename__ = "learning_bookmarks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_content.id", ondelete="CASCADE"), nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_learning_bookmarks_user_id", "user_id"),
        Index("ix_learning_bookmarks_content_id", "content_id"),
        UniqueConstraint("user_id", "content_id", name="uq_user_content_bookmark"),
    )


# ---------------------------------------------------------------------------
# Phase 5: Learning Paths & Modules
# ---------------------------------------------------------------------------

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Primary topic this path belongs to
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    # Eligibility & state
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en", nullable=False)
    audience: Mapped[str] = mapped_column(String(10), default="ALL", server_default="ALL", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modules: Mapped[list["LearningModule"]] = relationship(
        "LearningModule", back_populates="path", cascade="all, delete-orphan",
        order_by="LearningModule.display_order"
    )

    __table_args__ = (
        Index("ix_learning_paths_topic_id", "topic_id"),
        Index("ix_learning_paths_slug", "slug"),
        Index("ix_learning_paths_status", "status"),
        Index("ix_learning_paths_language", "language"),
        Index("ix_learning_paths_audience", "audience"),
    )


class LearningModule(Base):
    __tablename__ = "learning_modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    path_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

    path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="modules")
    
    items: Mapped[list["LearningModuleItem"]] = relationship(
        "LearningModuleItem", back_populates="module", cascade="all, delete-orphan",
        order_by="LearningModuleItem.display_order"
    )

    __table_args__ = (
        Index("ix_learning_modules_path_id", "path_id"),
    )


class LearningModuleItem(Base):
    """Junction table connecting a Module to LearningContent."""
    __tablename__ = "learning_module_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_content.id", ondelete="CASCADE"), nullable=False)
    
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    module: Mapped["LearningModule"] = relationship("LearningModule", back_populates="items")
    content: Mapped["LearningContent"] = relationship("LearningContent")

    __table_args__ = (
        Index("ix_learning_module_items_module_id", "module_id"),
        Index("ix_learning_module_items_content_id", "content_id"),
        UniqueConstraint("module_id", "content_id", name="uq_module_content_item"),
    )
