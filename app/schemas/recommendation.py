from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lesson import LessonSummary


class RecommendedLesson(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson: LessonSummary
    score: float = Field(ge=0)
    reason: str = Field(min_length=1, max_length=400)