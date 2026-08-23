from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.lesson import LessonSummary
from app.schemas.recommendation import RecommendedLesson
from app.services.analytics import AnalyticsService
from app.services.auth import StoredUser
from app.services.lessons import LessonService
from app.services.progress import ProgressService

SUPPORTED_ENGAGEMENT_EVENTS = {"lesson_view", "lesson_start", "lesson_complete"}


@dataclass(slots=True)
class _RecommendationCandidate:
    lesson: LessonSummary
    score: float
    reason: str


@dataclass(slots=True)
class _EngagementBucket:
    lesson_views: int = 0
    lesson_starts: int = 0
    lesson_completions: int = 0
    last_activity: datetime | None = None


class RecommendationService:
    def __init__(
        self,
        lesson_service: LessonService,
        progress_service: ProgressService,
        analytics_service: AnalyticsService | None = None,
    ) -> None:
        self._lesson_service = lesson_service
        self._progress_service = progress_service
        self._analytics_service = analytics_service

    def recommend_lessons(
        self,
        *,
        user: StoredUser,
        limit: int = 5,
        include_completed: bool = False,
        content_language: str | None = None,
    ) -> list[RecommendedLesson]:
        preferred_language = user.preferred_language.strip().lower()
        effective_content_language = content_language or preferred_language
        lessons = self._lesson_service.list_lessons(
            published_only=True,
            content_language=effective_content_language,
        )
        progress_items = self._progress_service.list_progress(user_id=user.id)
        engagement_signals = self._collect_engagement_signals(user.id)

        completed_ids = {item.lesson_id for item in progress_items if item.status == "completed"}
        category_counts = Counter(
            item.lesson.category
            for item in progress_items
            if item.status in {"in_progress", "completed"}
        )

        candidates: list[_RecommendationCandidate] = []
        for lesson in lessons:
            if not include_completed and lesson.id in completed_ids:
                continue

            score = 0.0
            reasons: list[str] = []

            if lesson.language == preferred_language:
                score += 30.0
                reasons.append("Matches your preferred language")

            category_count = category_counts.get(lesson.category, 0)
            if category_count:
                score += 20.0 + min((category_count - 1) * 5.0, 10.0)
                reasons.append(f"Builds on the {lesson.category} topics you have already explored")

            engagement_score, engagement_reasons = self._score_engagement(lesson, engagement_signals)
            if engagement_score:
                score += engagement_score
                reasons.extend(engagement_reasons)

            if lesson.id in completed_ids and include_completed:
                score += 5.0
                reasons.append("Useful for review after completion")

            if not reasons:
                reasons.append("Suggested as a good next lesson")

            candidates.append(
                _RecommendationCandidate(
                    lesson=lesson,
                    score=score,
                    reason="; ".join(dict.fromkeys(reasons)),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                -candidate.lesson.created_at.timestamp(),
                candidate.lesson.title.lower(),
            )
        )

        return [
            RecommendedLesson(lesson=candidate.lesson, score=round(candidate.score, 1), reason=candidate.reason)
            for candidate in candidates[:limit]
        ]

    def _collect_engagement_signals(self, user_id: str) -> dict[str, _EngagementBucket]:
        if self._analytics_service is None:
            return {}

        signals: dict[str, _EngagementBucket] = {}
        events = self._analytics_service.get_user_events(user_id=user_id, limit=500)
        for event in events:
            if event.event_type not in SUPPORTED_ENGAGEMENT_EVENTS:
                continue

            lesson_key = self._extract_lesson_key(event.metadata)
            if lesson_key is None:
                continue

            bucket = signals.setdefault(lesson_key, _EngagementBucket())
            if event.event_type == "lesson_view":
                bucket.lesson_views += 1
            elif event.event_type == "lesson_start":
                bucket.lesson_starts += 1
            elif event.event_type == "lesson_complete":
                bucket.lesson_completions += 1

            if bucket.last_activity is None or event.created_at > bucket.last_activity:
                bucket.last_activity = event.created_at

        return signals

    def _extract_lesson_key(self, metadata: dict[str, str]) -> str | None:
        lesson_id = metadata.get("lesson_id", "").strip()
        if lesson_id:
            return lesson_id

        lesson_slug = metadata.get("lesson_slug", "").strip().lower()
        if lesson_slug:
            return lesson_slug

        return None

    def _score_engagement(
        self,
        lesson: LessonSummary,
        signals: dict[str, _EngagementBucket],
    ) -> tuple[float, list[str]]:
        bucket = self._merge_buckets(lesson, signals)
        if bucket is None:
            return 0.0, []

        score = 0.0
        reasons: list[str] = []

        if bucket.lesson_views:
            score += min(bucket.lesson_views * 4.0, 12.0)
            reasons.append(
                "You have viewed this lesson before" if bucket.lesson_views == 1 else "You have viewed this lesson multiple times"
            )

        if bucket.lesson_starts:
            score += min(bucket.lesson_starts * 6.0, 18.0)
            reasons.append(
                "You have started this lesson before" if bucket.lesson_starts == 1 else "You have started this lesson multiple times"
            )

        if bucket.lesson_completions:
            score += min(bucket.lesson_completions * 10.0, 20.0)
            reasons.append(
                "You completed this lesson before" if bucket.lesson_completions == 1 else "You completed this lesson multiple times"
            )

        if bucket.last_activity is not None:
            age_days = (datetime.now(timezone.utc) - bucket.last_activity).total_seconds() / 86400
            if age_days <= 7:
                score += 8.0
                reasons.append("This lesson has recent activity")
            elif age_days <= 30:
                score += 4.0
                reasons.append("This lesson has recent engagement")

        return score, reasons

    def _merge_buckets(self, lesson: LessonSummary, signals: dict[str, _EngagementBucket]) -> _EngagementBucket | None:
        combined = _EngagementBucket()
        found = False

        for key in (lesson.id, lesson.slug):
            bucket = signals.get(key)
            if bucket is None:
                continue
            found = True
            combined.lesson_views += bucket.lesson_views
            combined.lesson_starts += bucket.lesson_starts
            combined.lesson_completions += bucket.lesson_completions
            if bucket.last_activity is not None and (
                combined.last_activity is None or bucket.last_activity > combined.last_activity
            ):
                combined.last_activity = bucket.last_activity

        return combined if found else None
