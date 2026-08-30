"""Pydantic schemas for the Learning Content System — Phase 1+2."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.monetization import SponsorResponse

# ---------------------------------------------------------------------------
# Literal types
# ---------------------------------------------------------------------------
ContentType = Literal["VIDEO", "ARTICLE", "POST", "TUTORIAL"]
SourceType = Literal["YOUTUBE", "PRIVATE_VIDEO", "INTERNAL", "INSTAGRAM"]
ContentStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED", "PENDING_REVIEW", "REJECTED", "UNDER_REVIEW", "MEDICALLY_REVIEWED", "NEEDS_REVIEW"]
Audience = Literal["ALL", "TEEN", "ADULT"]

VALID_COMBINATIONS: frozenset[tuple[str, str]] = frozenset(
    [
        ("VIDEO", "YOUTUBE"),
        ("VIDEO", "PRIVATE_VIDEO"),
        ("ARTICLE", "INTERNAL"),
        ("POST", "INTERNAL"),
        ("TUTORIAL", "INTERNAL"),
        ("TUTORIAL", "YOUTUBE"),
        ("TUTORIAL", "PRIVATE_VIDEO"),
        ("VIDEO", "INSTAGRAM"),
        ("POST", "INSTAGRAM"),
    ]
)

YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_\-]{11})"
)

# ---------------------------------------------------------------------------
# Topic / Subtopic schemas
# ---------------------------------------------------------------------------

class SubtopicResponse(BaseModel):
    id: str
    topic_id: str
    name: str
    slug: str
    description: Optional[str] = None
    display_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TopicResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int
    is_active: bool
    subtopics: List[SubtopicResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TopicsListResponse(BaseModel):
    items: List[TopicResponse]
    total: int


# ---------------------------------------------------------------------------
# Content Body Block schemas (for ARTICLE / POST / TUTORIAL)
# ---------------------------------------------------------------------------
VALID_BLOCK_TYPES = frozenset(
    ["heading", "paragraph", "image", "video", "important_box", "list", "callout"]
)


def validate_body_blocks(body: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    if body is None:
        return None
    for i, block in enumerate(body):
        if not isinstance(block, dict):
            raise ValueError(f"Block {i} must be a dict.")
        if "type" not in block:
            raise ValueError(f"Block {i} is missing 'type'.")
        if block["type"] not in VALID_BLOCK_TYPES:
            raise ValueError(
                f"Block {i} has unknown type '{block['type']}'. "
                f"Valid types: {VALID_BLOCK_TYPES}"
            )
    return body


# ---------------------------------------------------------------------------
# Base schema
# ---------------------------------------------------------------------------
class LearningContentBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    content_type: ContentType
    source_type: SourceType

    # For YOUTUBE content
    media_url: Optional[str] = Field(None, max_length=500)
    # For PRIVATE_VIDEO: media_files.id from the existing R2/psycopg system
    media_file_id: Optional[str] = None
    # Thumbnail: media_files.id
    thumbnail_file_id: Optional[str] = None

    # Article/Post/Tutorial body blocks — list of typed blocks
    body: Optional[List[Dict[str, Any]]] = None

    category: str = Field(..., max_length=50)
    tags: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)
    is_featured: bool = False
    is_short_form: bool = False
    status: ContentStatus = "DRAFT"
    duration_minutes: int = Field(default=0, ge=0)

    # Phase 1: Topic taxonomy
    topic_id: Optional[str] = None
    subtopic_id: Optional[str] = None

    # Phase 1: Audience targeting
    audience: Audience = "ALL"

    # Phase 1: Featured ranking (lower = more prominent)
    featured_rank: Optional[int] = None

    # Phase 1: Translation group for multi-language content
    translation_group_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_combination(self) -> "LearningContentBase":
        if (self.content_type, self.source_type) not in VALID_COMBINATIONS:
            raise ValueError(
                f"content_type='{self.content_type}' is not compatible with "
                f"source_type='{self.source_type}'. "
                f"Valid pairs: {list(VALID_COMBINATIONS)}"
            )
        return self

    @model_validator(mode="after")
    def validate_youtube_url(self) -> "LearningContentBase":
        if self.source_type == "YOUTUBE":
            if not self.media_url:
                raise ValueError("media_url is required for YOUTUBE content.")
            if not YOUTUBE_PATTERN.search(self.media_url):
                raise ValueError(
                    f"'{self.media_url}' is not a valid YouTube URL. "
                    "Expected: https://www.youtube.com/watch?v=XXXXXXXXXXX or https://youtu.be/XXXXXXXXXXX"
                )
        return self

    @model_validator(mode="after")
    def validate_private_video(self) -> "LearningContentBase":
        if self.source_type == "PRIVATE_VIDEO" and not self.media_file_id:
            raise ValueError("media_file_id is required for PRIVATE_VIDEO content.")
        return self

    @field_validator("body", mode="before")
    @classmethod
    def validate_body(cls, v: Any) -> Any:
        return validate_body_blocks(v)


class LearningContentCreate(LearningContentBase):
    pass


class LearningContentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    content_type: Optional[ContentType] = None
    source_type: Optional[SourceType] = None
    media_url: Optional[str] = Field(None, max_length=500)
    media_file_id: Optional[str] = None
    thumbnail_file_id: Optional[str] = None
    body: Optional[List[Dict[str, Any]]] = None
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    language: Optional[str] = Field(None, max_length=10)
    is_featured: Optional[bool] = None
    is_short_form: Optional[bool] = None
    status: Optional[ContentStatus] = None
    duration_minutes: Optional[int] = Field(None, ge=0)
    # Phase 1
    topic_id: Optional[str] = None
    subtopic_id: Optional[str] = None
    audience: Optional[Audience] = None
    featured_rank: Optional[int] = None
    translation_group_id: Optional[str] = None

    @field_validator("body", mode="before")
    @classmethod
    def validate_body(cls, v: Any) -> Any:
        return validate_body_blocks(v)


class MedicalReviewRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class LearningContentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    content_type: str
    source_type: str
    media_url: Optional[str]
    media_file_id: Optional[str]
    thumbnail_file_id: Optional[str]
    thumbnail_url: Optional[str] = None
    media_file_url: Optional[str] = None
    body: Optional[List[Dict[str, Any]]]
    category: str
    tags: List[str]
    language: str
    is_featured: bool
    is_short_form: bool
    status: str
    duration_minutes: int
    author_id: str
    # Phase 1
    topic_id: Optional[str] = None
    subtopic_id: Optional[str] = None
    audience: str = "ALL"
    featured_rank: Optional[int] = None
    translation_group_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    # Phase 8: Medical Trust
    medical_review_status: str = "NOT_REVIEWED"
    medical_reviewer_id: Optional[str] = None
    medical_reviewed_at: Optional[datetime] = None

    # Phase 10: Sponsorship
    sponsor_id: Optional[str] = None
    sponsor: Optional[SponsorResponse] = None

    model_config = ConfigDict(from_attributes=True)


class LearningContentListResponse(BaseModel):
    items: List[LearningContentResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Recommendation schemas (Phase 7)
# ---------------------------------------------------------------------------
class RecommendationResponse(BaseModel):
    content: LearningContentResponse
    reason: str
    score: float

class RecommendationListResponse(BaseModel):
    items: List[RecommendationResponse]
    total: int
    page: int
    page_size: int

# ---------------------------------------------------------------------------
# Progress schemas
# ---------------------------------------------------------------------------
class LearningProgressUpdate(BaseModel):
    completed: bool = False
    watch_time_seconds: int = Field(default=0, ge=0)
    progress_percent: int = Field(default=0, ge=0, le=100)


class LearningProgressResponse(BaseModel):
    user_id: str
    content_id: str
    completed: bool
    watch_time_seconds: int
    progress_percent: int
    view_count: int = 0
    last_accessed_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StreakResponse(BaseModel):
    current: int
    longest: int

class BadgeResponse(BaseModel):
    key: str
    earned_at: datetime

class LearningSummaryResponse(BaseModel):
    completed_lessons: int
    learning_minutes: int
    articles_read: int = 0
    videos_watched: int = 0
    paths_started: int = 0
    paths_completed: int = 0
    topics_explored: List[str] = Field(default_factory=list)
    favorite_format: Optional[str] = None
    continue_learning: Optional[LearningContentResponse] = None
    streak: Optional[StreakResponse] = None
    badges: List[BadgeResponse] = Field(default_factory=list)

class LearningHistoryItemResponse(BaseModel):
    progress: LearningProgressResponse
    content: LearningContentResponse

class LearningHistoryResponse(BaseModel):
    items: List[LearningHistoryItemResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Phase 5: Learning Path & Module Schemas
# ---------------------------------------------------------------------------

class LearningModuleItemResponse(BaseModel):
    id: str
    module_id: str
    content_id: str
    display_order: int
    is_required: bool
    content: LearningContentResponse

    model_config = ConfigDict(from_attributes=True)

class LearningModuleResponse(BaseModel):
    id: str
    path_id: str
    title: str
    description: Optional[str]
    display_order: int
    items: List[LearningModuleItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class LearningPathResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    topic_id: str
    language: str
    audience: str
    status: str
    display_order: int
    is_featured: bool
    modules: List[LearningModuleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class LearningPathListResponse(BaseModel):
    items: List[LearningPathResponse]
    total: int
    page: int
    page_size: int

class LearningPathProgressResponse(BaseModel):
    path_id: str
    completed_content: int
    total_content: int
    progress_percent: int
    # Mapping of module_id -> { completed: int, total: int }
    module_progress: Dict[str, Dict[str, int]]

