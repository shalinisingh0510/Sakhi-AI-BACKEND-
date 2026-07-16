from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.lesson import LessonSummary

ProgressStatus = Literal["not_started", "in_progress", "completed"]


class LessonProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lesson_id: str
    lesson: LessonSummary
    status: ProgressStatus
    progress_percent: int
    notes: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime


class ProgressOverview(BaseModel):
    total_lessons: int
    completed_lessons: int
    in_progress_lessons: int
    not_started_lessons: int
    completion_rate: float
    average_progress_percent: float


class UpdateProgressRequest(BaseModel):
    status: ProgressStatus = "in_progress"
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().lower()
