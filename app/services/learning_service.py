"""Learning Content Service — business logic layer for Sakhi AI Learning System.

Phase 1 additions:
  - Topic / Subtopic taxonomy methods
  - topic_id / subtopic_id / audience filtering in get_feed
  - Translation group support (architecture)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select, String
from sqlalchemy.orm import Session, selectinload

from app.models.learning import (
    VALID_COMBINATIONS,
    LearningContent,
    LearningProgress,
    LearningBookmark,
    LearningPath,
    LearningModule,
    LearningModuleItem,
    Topic,
    Subtopic,
    extract_youtube_id,
    validate_content_combination,
)


class LearningContentNotFoundError(ValueError):
    pass


class InvalidContentError(ValueError):
    pass


class TopicNotFoundError(ValueError):
    pass


from app.services.storage import StorageServiceProtocol

class LearningService:
    def __init__(self, db: Session, storage_service: Optional[StorageServiceProtocol] = None) -> None:
        self._db = db
        self._storage_service = storage_service

    def _resolve_urls(self, content: LearningContent) -> LearningContent:
        """Inject resolved presigned URLs if a storage service is available."""
        if not self._storage_service:
            return content

        if content.thumbnail_file_id:
            try:
                content.thumbnail_url = self._storage_service.generate_presigned_download_url(
                    content.thumbnail_file_id
                )
            except Exception:
                pass  # Silently fail if storage is down

        if content.media_file_id:
            try:
                content.media_file_url = self._storage_service.generate_presigned_download_url(
                    content.media_file_id
                )
            except Exception:
                pass

        if content.body:
            for block in content.body:
                if block.get("media_file_id"):
                    try:
                        block["url"] = self._storage_service.generate_presigned_download_url(
                            block["media_file_id"]
                        )
                    except Exception:
                        pass

        return content

    # ------------------------------------------------------------------
    # Topic / Subtopic methods (Phase 1)
    # ------------------------------------------------------------------

    def get_topics(self, active_only: bool = True) -> List[Topic]:
        """Return all topics with their subtopics eagerly loaded."""
        query = select(Topic).options(selectinload(Topic.subtopics))
        if active_only:
            query = query.where(Topic.is_active.is_(True))
        query = query.order_by(Topic.display_order)
        return list(self._db.scalars(query).all())

    def get_topic_by_slug(self, slug: str) -> Topic:
        """Return a single topic by slug (with subtopics)."""
        topic = self._db.scalar(
            select(Topic)
            .options(selectinload(Topic.subtopics))
            .where(Topic.slug == slug)
        )
        if not topic:
            raise TopicNotFoundError(f"Topic '{slug}' not found.")
        return topic

    def get_topic_content(
        self,
        topic_slug: str,
        subtopic_slug: Optional[str] = None,
        content_type: Optional[str] = None,
        language: Optional[str] = None,
        audience: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[LearningContent], int]:
        """Return published content filtered by topic (and optionally subtopic)."""
        topic = self.get_topic_by_slug(topic_slug)

        query = select(LearningContent).where(
            and_(
                LearningContent.status == "PUBLISHED",
                LearningContent.topic_id == topic.id,
            )
        )

        if subtopic_slug:
            subtopic = self._db.scalar(
                select(Subtopic).where(
                    and_(Subtopic.topic_id == topic.id, Subtopic.slug == subtopic_slug)
                )
            )
            if subtopic:
                query = query.where(LearningContent.subtopic_id == subtopic.id)

        if content_type:
            query = query.where(LearningContent.content_type == content_type)
        if language:
            query = query.where(LearningContent.language == language)
        if audience:
            if audience == "TEEN":
                query = query.where(LearningContent.audience.in_(["TEEN", "ALL"]))
            elif audience == "ADULT":
                query = query.where(LearningContent.audience.in_(["ADULT", "ALL"]))
            else:
                query = query.where(LearningContent.audience == audience)

        total_count = self._db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        query = query.order_by(
            LearningContent.featured_rank.asc().nulls_last(),
            LearningContent.published_at.desc().nulls_last(),
            LearningContent.created_at.desc(),
        ).offset(offset).limit(limit)

        results = self._db.scalars(query).all()
        return [self._resolve_urls(c) for c in results], total_count

    # ------------------------------------------------------------------
    # Public (user-facing) methods
    # ------------------------------------------------------------------

    def get_feed(
        self,
        category: Optional[str] = None,
        content_type: Optional[str] = None,
        language: Optional[str] = None,
        is_featured: Optional[bool] = None,
        search: Optional[str] = None,
        topic_id: Optional[str] = None,
        subtopic_id: Optional[str] = None,
        audience: Optional[str] = None,
        is_short_form: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[LearningContent], int]:
        query = select(LearningContent).where(LearningContent.status == "PUBLISHED")

        if category:
            query = query.where(LearningContent.category == category)
        if content_type:
            query = query.where(LearningContent.content_type == content_type)
        if language:
            query = query.where(LearningContent.language == language)
        if is_featured is not None:
            query = query.where(LearningContent.is_featured == is_featured)
        if is_short_form is not None:
            query = query.where(LearningContent.is_short_form == is_short_form)
        if search:
            like_term = f"%{search}%"
            query = query.where(
                LearningContent.title.ilike(like_term)
                | LearningContent.description.ilike(like_term)
                | func.cast(LearningContent.tags, String).ilike(like_term)
            )
        if topic_id:
            query = query.where(LearningContent.topic_id == topic_id)
        if subtopic_id:
            query = query.where(LearningContent.subtopic_id == subtopic_id)
        if audience:
            if audience == "TEEN":
                query = query.where(LearningContent.audience.in_(["TEEN", "ALL"]))
            elif audience == "ADULT":
                query = query.where(LearningContent.audience.in_(["ADULT", "ALL"]))
            else:
                query = query.where(LearningContent.audience == audience)

        total_count = self._db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        query = query.order_by(
            LearningContent.featured_rank.asc().nulls_last(),
            LearningContent.created_at.desc(),
        ).offset(offset).limit(limit)
        results = self._db.scalars(query).all()
        return [self._resolve_urls(c) for c in results], total_count

    def get_content(self, content_id: str, admin: bool = False) -> LearningContent:
        """Fetch a content item.  By default only PUBLISHED content is visible.
        Pass admin=True to allow DRAFT/ARCHIVED access (admin panel)."""
        content = self._db.get(LearningContent, content_id)
        if not content:
            raise LearningContentNotFoundError(f"Content '{content_id}' not found.")
        if not admin and content.status != "PUBLISHED":
            raise LearningContentNotFoundError(f"Content '{content_id}' not found.")
        return self._resolve_urls(content)

    def get_progress(self, user_id: str, content_id: str) -> Optional[LearningProgress]:
        return self._db.get(LearningProgress, (user_id, content_id))

    def get_user_progress_summary(self, user_id: str) -> dict:
        completed_count = (
            self._db.scalar(
                select(func.count(LearningProgress.content_id)).where(
                    and_(
                        LearningProgress.user_id == user_id,
                        LearningProgress.completed.is_(True),
                    )
                )
            )
            or 0
        )

        watch_time = (
            self._db.scalar(
                select(func.sum(LearningProgress.watch_time_seconds)).where(
                    LearningProgress.user_id == user_id
                )
            )
            or 0
        )

        # Count videos watched (completed video content)
        videos_watched = (
            self._db.scalar(
                select(func.count(LearningProgress.content_id))
                .join(LearningContent, LearningContent.id == LearningProgress.content_id)
                .where(
                    and_(
                        LearningProgress.user_id == user_id,
                        LearningProgress.completed.is_(True),
                        LearningContent.content_type == "VIDEO",
                    )
                )
            )
            or 0
        )

        articles_read = (
            self._db.scalar(
                select(func.count(LearningProgress.content_id))
                .join(LearningContent, LearningContent.id == LearningProgress.content_id)
                .where(
                    and_(
                        LearningProgress.user_id == user_id,
                        LearningProgress.completed.is_(True),
                        LearningContent.content_type.in_(["ARTICLE", "POST"]),
                    )
                )
            )
            or 0
        )

        # Fetch most recently accessed unfinished content
        continue_learning_record = self._db.scalars(
            select(LearningContent)
            .join(LearningProgress, LearningContent.id == LearningProgress.content_id)
            .where(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.completed.is_(False),
                    LearningContent.status == "PUBLISHED"
                )
            )
            .order_by(LearningProgress.last_accessed_at.desc())
            .limit(1)
        ).first()

        continue_learning = None
        if continue_learning_record:
            continue_learning = self._resolve_urls(continue_learning_record)

        # Gamification logic
        streak = {"current": 0, "longest": 0}
        badges = []
        try:
            from app.services.gamification_service import GamificationService
            from app.models.gamification import UserGamification, UserBadge
            g_svc = GamificationService(self._db)
            g = g_svc.get_user_gamification(user_id)
            streak["current"] = g.current_streak
            streak["longest"] = g.longest_streak
            
            user_badges = self._db.scalars(
                select(UserBadge).where(UserBadge.user_id == user_id)
            ).all()
            badges = [{"key": b.badge_key, "earned_at": b.earned_at} for b in user_badges]
        except Exception:
            pass

        return {
            "completed_lessons": completed_count,
            "learning_minutes": watch_time // 60,
            "videos_watched": videos_watched,
            "articles_read": articles_read,
            "continue_learning": continue_learning,
            "streak": streak,
            "badges": badges,
        }

    def get_learning_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[dict]:
        query = (
            select(LearningProgress, LearningContent)
            .join(LearningContent, LearningContent.id == LearningProgress.content_id)
            .where(LearningProgress.user_id == user_id)
            .order_by(LearningProgress.last_accessed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        results = self._db.execute(query).all()
        history = []
        for progress, content in results:
            resolved_content = self._resolve_urls(content)
            history.append({
                "progress": progress,
                "content": resolved_content,
            })
        return history

    def toggle_bookmark(self, user_id: str, content_id: str) -> bool:
        """Toggles a bookmark. Returns True if saved, False if unsaved."""
        bookmark = self._db.scalar(
            select(LearningBookmark).where(
                and_(LearningBookmark.user_id == user_id, LearningBookmark.content_id == content_id)
            )
        )
        if bookmark:
            self._db.delete(bookmark)
            self._db.commit()
            return False
        else:
            new_bookmark = LearningBookmark(user_id=user_id, content_id=content_id)
            self._db.add(new_bookmark)
            self._db.commit()
            return True

    def get_bookmarks(self, user_id: str, limit: int = 20, offset: int = 0) -> List[LearningContent]:
        query = (
            select(LearningContent)
            .join(LearningBookmark, LearningBookmark.content_id == LearningContent.id)
            .where(LearningBookmark.user_id == user_id)
            .order_by(LearningBookmark.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        results = self._db.scalars(query).all()
        return [self._resolve_urls(c) for c in results]

    def update_progress(
        self,
        user_id: str,
        content_id: str,
        completed: bool = False,
        watch_time_seconds: int = 0,
        progress_percent: int = 0,
    ) -> LearningProgress:
        progress = self._db.get(LearningProgress, (user_id, content_id))
        now = datetime.utcnow()

        if not progress:
            progress = LearningProgress(
                user_id=user_id,
                content_id=content_id,
                completed=completed,
                watch_time_seconds=watch_time_seconds,
                progress_percent=progress_percent,
                view_count=1,
                last_accessed_at=now,
                completed_at=now if completed else None,
            )
            self._db.add(progress)
        else:
            if watch_time_seconds > 0:
                progress.watch_time_seconds = watch_time_seconds
            if progress_percent > progress.progress_percent:
                progress.progress_percent = progress_percent
            if completed and not progress.completed:
                progress.completed = True
                progress.completed_at = now
            
            # Increment view count if it's been more than an hour since last access
            if (now - progress.last_accessed_at).total_seconds() > 3600:
                progress.view_count += 1
                
            progress.last_accessed_at = now

        self._db.commit()
        self._db.refresh(progress)
        
        # Trigger gamification check-in for meaningful learning activity
        try:
            from app.services.gamification_service import GamificationService
            GamificationService(self._db).record_checkin(user_id, now.date())
        except Exception:
            pass
            
        return progress

    # ------------------------------------------------------------------
    # Phase 5: Learning Paths Methods
    # ------------------------------------------------------------------

    def get_paths(
        self,
        topic_slug: Optional[str] = None,
        language: Optional[str] = None,
        audience: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[LearningPath], int]:
        query = select(LearningPath).where(LearningPath.status == "PUBLISHED")

        if topic_slug:
            topic = self.get_topic_by_slug(topic_slug)
            query = query.where(LearningPath.topic_id == topic.id)
            
        if language:
            query = query.where(LearningPath.language == language)
            
        if audience:
            if audience == "TEEN":
                query = query.where(LearningPath.audience.in_(["TEEN", "ALL"]))
            elif audience == "ADULT":
                query = query.where(LearningPath.audience.in_(["ADULT", "ALL"]))
            else:
                query = query.where(LearningPath.audience == audience)

        total_count = self._db.scalar(select(func.count()).select_from(query.subquery())) or 0
        
        query = query.order_by(
            LearningPath.display_order.asc(),
            LearningPath.published_at.desc().nulls_last()
        ).offset(offset).limit(limit)
        
        return list(self._db.scalars(query).all()), total_count

    def get_path_by_slug(self, slug: str) -> LearningPath:
        path = self._db.scalar(
            select(LearningPath)
            .options(
                selectinload(LearningPath.modules).selectinload(LearningModule.items).selectinload(LearningModuleItem.content)
            )
            .where(LearningPath.slug == slug)
        )
        if not path:
            raise ValueError(f"Learning Path '{slug}' not found.")
            
        # Resolve URLs for all content in the path
        for module in path.modules:
            for item in module.items:
                item.content = self._resolve_urls(item.content)
                
        return path

    def get_path_progress(self, user_id: str, path_id: str) -> dict:
        """Calculate progress for a learning path for a given user."""
        path = self._db.scalar(
            select(LearningPath)
            .options(selectinload(LearningPath.modules).selectinload(LearningModule.items))
            .where(LearningPath.id == path_id)
        )
        
        if not path:
            raise ValueError(f"Learning Path '{path_id}' not found.")

        # Extract all content IDs in this path
        module_contents = {}
        all_content_ids = []
        
        for module in path.modules:
            c_ids = [item.content_id for item in module.items]
            module_contents[module.id] = c_ids
            all_content_ids.extend(c_ids)
            
        if not all_content_ids:
            return {
                "path_id": path_id,
                "completed_content": 0,
                "total_content": 0,
                "progress_percent": 0,
                "module_progress": {}
            }

        # Fetch progress for these content IDs
        progress_records = self._db.scalars(
            select(LearningProgress).where(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.content_id.in_(all_content_ids),
                    LearningProgress.completed.is_(True)
                )
            )
        ).all()
        
        completed_set = {p.content_id for p in progress_records}
        
        # Calculate per-module progress
        module_progress = {}
        for mod_id, c_ids in module_contents.items():
            completed_in_mod = sum(1 for cid in c_ids if cid in completed_set)
            module_progress[mod_id] = {
                "completed": completed_in_mod,
                "total": len(c_ids)
            }
            
        total_completed = len(completed_set)
        total_content = len(all_content_ids)
        progress_percent = int((total_completed / total_content) * 100) if total_content > 0 else 0
        
        return {
            "path_id": path_id,
            "completed_content": total_completed,
            "total_content": total_content,
            "progress_percent": progress_percent,
            "module_progress": module_progress
        }

    def get_related_content(self, content_id: str, limit: int = 4) -> List[LearningContent]:
        content = self.get_content(content_id)
        if not content:
            return []

        # If content has a topic, prefer topic-based related content
        filters = [
            LearningContent.status == "PUBLISHED",
            LearningContent.id != content_id,
        ]
        if content.topic_id:
            filters.append(LearningContent.topic_id == content.topic_id)
        else:
            filters.append(LearningContent.category == content.category)

        query = select(LearningContent).where(and_(*filters)).order_by(
            LearningContent.created_at.desc()
        ).limit(limit)

        results = self._db.scalars(query).all()
        return [self._resolve_urls(c) for c in results]

    # ------------------------------------------------------------------
    # Admin methods
    # ------------------------------------------------------------------

    def get_admin_list(
        self,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        topic_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[LearningContent], int]:
        query = select(LearningContent)
        if status:
            query = query.where(LearningContent.status == status)
        if content_type:
            query = query.where(LearningContent.content_type == content_type)
        if category:
            query = query.where(LearningContent.category == category)
        if topic_id:
            query = query.where(LearningContent.topic_id == topic_id)
        if search:
            query = query.where(LearningContent.title.ilike(f"%{search}%"))

        total_count = self._db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0
        query = query.order_by(LearningContent.created_at.desc()).offset(offset).limit(limit)
        results = self._db.scalars(query).all()
        return [self._resolve_urls(c) for c in results], total_count

    def create_content(self, author_id: str, data: dict) -> LearningContent:
        validate_content_combination(data["content_type"], data["source_type"])
        content = LearningContent(author_id=author_id, **data)
        self._db.add(content)
        self._db.commit()
        self._db.refresh(content)
        return content

    def update_content(self, content_id: str, data: dict) -> LearningContent:
        content = self._db.get(LearningContent, content_id)
        if not content:
            raise LearningContentNotFoundError(f"Content '{content_id}' not found.")

        # If changing content_type or source_type, revalidate
        new_ctype = data.get("content_type", content.content_type)
        new_stype = data.get("source_type", content.source_type)
        validate_content_combination(new_ctype, new_stype)

        for key, value in data.items():
            setattr(content, key, value)

        self._db.commit()
        self._db.refresh(content)
        return content

    def publish_content(self, content_id: str) -> LearningContent:
        content = self.get_content(content_id, admin=True)
        content.status = "PUBLISHED"
        content.published_at = datetime.utcnow()
        self._db.commit()
        self._db.refresh(content)
        return content

    def archive_content(self, content_id: str) -> LearningContent:
        content = self.get_content(content_id, admin=True)
        content.status = "ARCHIVED"
        self._db.commit()
        self._db.refresh(content)
        return content

    def delete_content(self, content_id: str) -> None:
        """Hard delete. LearningProgress rows are cascade-deleted via FK."""
        content = self._db.get(LearningContent, content_id)
        if not content:
            raise LearningContentNotFoundError(f"Content '{content_id}' not found.")
        self._db.delete(content)
        self._db.commit()
