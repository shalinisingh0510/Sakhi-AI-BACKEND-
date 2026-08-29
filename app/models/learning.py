"""Learning Content System models for Sakhi AI.

LearningContent supports:
  - VIDEO (source: YOUTUBE or PRIVATE_VIDEO)
  - ARTICLE (source: INTERNAL)
  - POST (source: INTERNAL)

Private media assets reference the existing media_files table (psycopg-based, not Alembic-managed).
Thumbnails also reference media_files.
"""

from __future__ import annotations

import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Index, String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
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


class LearningContent(Base):
    __tablename__ = "learning_content"
    __allow_unmapped__ = True

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # VIDEO, ARTICLE, or POST
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # YOUTUBE, PRIVATE_VIDEO, or INTERNAL
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # For YOUTUBE: the full URL (e.g. https://www.youtube.com/watch?v=XXXXX)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # For PRIVATE_VIDEO: references media_files.id (psycopg-managed, NOT Alembic FK)
    # We store as plain String to avoid cross-ORM FK constraints
    media_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Thumbnail: also references media_files.id
    thumbnail_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Structured JSON body for ARTICLE / POST content blocks:
    # [{"type": "heading", "text": "..."}, {"type": "paragraph", "text": "..."}, ...]
    body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Content classification
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")

    # Authorship — references users table id (not FK-constrained to avoid cross-store issues)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Status: DRAFT | PUBLISHED | ARCHIVED
    # Architecture is forward-compatible with PENDING_REVIEW | REJECTED for doctor workflow
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)

    # Optional extras
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
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

    # Transient attributes for resolved URLs
    thumbnail_url: str | None = None
    media_file_url: str | None = None

    __table_args__ = (
        Index("ix_learning_content_status", "status"),
        Index("ix_learning_content_category", "category"),
        Index("ix_learning_content_content_type", "content_type"),
        Index("ix_learning_content_created_at", "created_at"),
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
