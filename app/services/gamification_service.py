from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.gamification import UserGamification, UserBadge

class GamificationService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_gamification(self, user_id: str) -> UserGamification:
        g = self.db.scalars(select(UserGamification).where(UserGamification.user_id == user_id)).first()
        if not g:
            g = UserGamification(user_id=user_id)
            self.db.add(g)
            self.db.commit()
            self.db.refresh(g)
        return g

    def record_checkin(self, user_id: str, checkin_date: date) -> dict:
        """
        Record a daily check-in, update streaks, and award XP.
        Returns gamification delta (e.g. XP earned, new level, new badges).
        """
        g = self.get_user_gamification(user_id)
        
        # We assume check-ins are logged in UTC or server local time, but we just compare dates.
        # Ensure we only give XP once per day
        last_date = g.last_checkin_date.date() if g.last_checkin_date else None
        
        delta = {"xp_earned": 0, "leveled_up": False, "new_badges": []}
        
        if last_date == checkin_date:
            return delta # Already checked in today
            
        # Update streak
        if last_date == checkin_date - timedelta(days=1):
            g.current_streak += 1
        else:
            g.current_streak = 1
            
        if g.current_streak > g.longest_streak:
            g.longest_streak = g.current_streak
            
        g.last_checkin_date = datetime.now(timezone.utc)
        
        # Award XP
        xp_to_add = 10
        g.xp += xp_to_add
        delta["xp_earned"] = xp_to_add
        
        # Level up calculation (simple: 100 XP = 1 level)
        new_level = (g.xp // 100) + 1
        if new_level > g.level:
            g.level = new_level
            delta["leveled_up"] = True
            
        # Badges check
        if g.current_streak == 7:
            badge_earned = self._award_badge(user_id, "STREAK_7")
            if badge_earned:
                delta["new_badges"].append("STREAK_7")
                
        self.db.commit()
        return delta
        
    def _award_badge(self, user_id: str, badge_key: str) -> bool:
        existing = self.db.scalars(select(UserBadge).where(
            UserBadge.user_id == user_id, 
            UserBadge.badge_key == badge_key
        )).first()
        
        if existing:
            return False
            
        b = UserBadge(user_id=user_id, badge_key=badge_key, earned_at=datetime.now(timezone.utc))
        self.db.add(b)
        return True

    def evaluate_learning_badges(self, user_id: str) -> list[str]:
        """
        Evaluate and award learning-specific badges.
        """
        from app.models.learning import LearningProgress, LearningPath, LearningModule, LearningModuleItem
        from sqlalchemy import func, and_

        new_badges = []
        
        # Check FIRST_LESSON and SCHOLAR_10
        completed_lessons = self.db.scalar(
            select(func.count(LearningProgress.content_id)).where(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.completed.is_(True)
                )
            )
        ) or 0
        
        if completed_lessons >= 1:
            if self._award_badge(user_id, "FIRST_LESSON"):
                new_badges.append("FIRST_LESSON")
        if completed_lessons >= 10:
            if self._award_badge(user_id, "SCHOLAR_10"):
                new_badges.append("SCHOLAR_10")
                
        # Check PATH_COMPLETER
        total_items_sq = (
            select(
                LearningPath.id.label("path_id"),
                func.count(LearningModuleItem.id).label("total_items")
            )
            .join(LearningModule, LearningModule.path_id == LearningPath.id)
            .join(LearningModuleItem, LearningModuleItem.module_id == LearningModule.id)
            .group_by(LearningPath.id)
        ).subquery()

        completed_items_sq = (
            select(
                LearningPath.id.label("path_id"),
                func.count(LearningModuleItem.id).label("completed_items")
            )
            .join(LearningModule, LearningModule.path_id == LearningPath.id)
            .join(LearningModuleItem, LearningModuleItem.module_id == LearningModule.id)
            .join(LearningProgress, LearningProgress.content_id == LearningModuleItem.content_id)
            .where(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.completed.is_(True)
                )
            )
            .group_by(LearningPath.id)
        ).subquery()

        paths_completed = self.db.scalar(
            select(func.count(total_items_sq.c.path_id))
            .join(completed_items_sq, total_items_sq.c.path_id == completed_items_sq.c.path_id)
            .where(total_items_sq.c.total_items == completed_items_sq.c.completed_items)
            .where(total_items_sq.c.total_items > 0)
        ) or 0
        
        if paths_completed >= 1:
            if self._award_badge(user_id, "PATH_COMPLETER"):
                new_badges.append("PATH_COMPLETER")
                
        if new_badges:
            self.db.commit()
            
        return new_badges
