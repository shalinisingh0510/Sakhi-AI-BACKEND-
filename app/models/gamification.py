from datetime import datetime
from uuid import uuid4
from sqlalchemy import Integer, String, DateTime, ForeignKey, Index, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class UserGamification(Base):
    """Tracks XP, Levels, and Streaks for Gamification."""
    __tablename__ = "user_gamification"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    last_checkin_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserBadge(Base):
    """Tracks badges earned by the user."""
    __tablename__ = "user_badges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    badge_key: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "FIRST_CHECKIN", "STREAK_7"
    
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("ix_user_badges_user_id", "user_id"),
    )
