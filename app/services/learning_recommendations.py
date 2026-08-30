from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import Session

from app.models.learning import (
    LearningContent,
    LearningProgress,
    LearningBookmark,
    LearningPath,
    LearningModuleItem,
)
from app.schemas.learning import RecommendationResponse, LearningContentResponse
from app.services.learning_service import LearningService


class LearningRecommendationService:
    def __init__(self, db: Session, learning_service: LearningService) -> None:
        self._db = db
        self._learning_service = learning_service

    def get_recommendations(
        self,
        user_id: str,
        preferred_language: str = "en",
        audience: str = "ALL",
        limit: int = 10,
        include_completed: bool = False,
    ) -> List[RecommendationResponse]:
        # 1. Fetch user's progress and bookmarks
        progress_items = self._db.scalars(
            select(LearningProgress).where(LearningProgress.user_id == user_id)
        ).all()
        
        bookmarks = self._db.scalars(
            select(LearningBookmark).where(LearningBookmark.user_id == user_id)
        ).all()

        bookmarked_content_ids = {b.content_id for b in bookmarks}
        
        completed_ids = {p.content_id for p in progress_items if p.completed or p.progress_percent == 100}
        in_progress_ids = {p.content_id for p in progress_items if not p.completed and p.progress_percent > 0 and p.progress_percent < 100}

        # Determine topic interest (using category/topic_id as proxy for topic)
        topic_counts_db = self._db.execute(
            select(LearningContent.topic_id, func.count())
            .join(LearningProgress, LearningProgress.content_id == LearningContent.id)
            .where(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningContent.topic_id.isnot(None)
                )
            )
            .group_by(LearningContent.topic_id)
        ).all()
        topic_counts = Counter({t[0]: t[1] for t in topic_counts_db})
                
        # Active learning paths: a heuristic is if they have progress on any item in a path
        # For simplicity, we just boost based on topic/category. A true path next item is slightly complex in one pass.
        
        # 2. Fetch candidates
        query = select(LearningContent).where(LearningContent.status == "PUBLISHED")
        
        # Language matching
        query = query.where(LearningContent.language == preferred_language)
        
        # Audience matching
        if audience == "TEEN":
            query = query.where(LearningContent.audience.in_(["TEEN", "ALL"]))
        elif audience == "ADULT":
            query = query.where(LearningContent.audience.in_(["ADULT", "ALL"]))
            
        candidates = self._db.scalars(query).all()
        
        recommendations = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for content in candidates:
            if not include_completed and content.id in completed_ids:
                continue

            score = 0.0
            reasons = []

            # CONTINUE LEARNING
            if content.id in in_progress_ids:
                score += 50.0
                reasons.append("Continue Learning")
                
            # BOOKMARK
            if content.id in bookmarked_content_ids:
                score += 30.0
                reasons.append("From your bookmarks")
                
            # TOPIC INTEREST
            if content.topic_id and topic_counts.get(content.topic_id, 0) > 0:
                topic_interest = min(topic_counts[content.topic_id] * 5.0, 20.0)
                score += topic_interest
                if "Continue Learning" not in reasons:
                    reasons.append("Because you explored this topic")

            # FRESHNESS
            if content.created_at:
                age_days = (now - content.created_at).total_seconds() / 86400
                if age_days <= 14:
                    score += 10.0
                    if not reasons:
                        reasons.append("New content")

            # FEATURED
            if content.is_featured:
                score += 15.0
                if not reasons:
                    reasons.append("Featured")
                    
            if not reasons:
                reasons.append("Recommended for you")

            # Convert to response
            content_with_urls = self._learning_service._resolve_urls(content)
            content_resp = LearningContentResponse.model_validate(content_with_urls)
            
            recommendations.append((content_resp, score, reasons[0]))

        # Sort by score descending, then by created_at descending
        recommendations.sort(key=lambda x: (-x[1], -x[0].created_at.timestamp()))
        
        # Deduplicate and return
        final_results = []
        for content_resp, score, reason in recommendations[:limit]:
            final_results.append(
                RecommendationResponse(
                    content=content_resp,
                    reason=reason,
                    score=score
                )
            )
            
        return final_results
