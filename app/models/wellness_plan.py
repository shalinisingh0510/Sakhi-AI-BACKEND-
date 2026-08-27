from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.db.base import Base

class PlanFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class PlanStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    DISMISSED = "DISMISSED"

class WellnessGoal(Base):
    """
    User-selected wellness goals (e.g. Better Nutrition, Consistent Activity).
    """
    __tablename__ = "wellness_goals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    goal_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., 'BETTER_NUTRITION'
    priority: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    plans: Mapped[List["WellnessPlan"]] = relationship("WellnessPlan", back_populates="goal")

class WellnessPlan(Base):
    """
    A specific generated action plan for a user based on their goals and longitudinal data.
    """
    __tablename__ = "wellness_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    goal_id: Mapped[Optional[str]] = mapped_column(ForeignKey("wellness_goals.id"))
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)  # e.g., 'LOG_BREAKFAST', 'SHORT_WALK'
    frequency: Mapped[PlanFrequency] = mapped_column(Enum(PlanFrequency), default=PlanFrequency.DAILY)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.SUGGESTED)
    
    # Explainability fields
    reasoning: Mapped[str] = mapped_column(String)
    source_evidence: Mapped[Optional[dict]] = mapped_column(JSONB) # Context/RAG used to generate
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    goal: Mapped[Optional["WellnessGoal"]] = relationship("WellnessGoal", back_populates="plans")
