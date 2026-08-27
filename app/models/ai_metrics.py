from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base

class AIModelProvider(str, enum.Enum):
    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
    GROQ = "GROQ"
    LOCAL = "LOCAL"

class AIObservabilityLog(Base):
    """
    Tracks AI cost, latency, and performance safely without logging PII/Health Context.
    """
    __tablename__ = "ai_observability_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Tracking identifiers
    request_id: Mapped[str] = mapped_column(String, index=True)
    task_type: Mapped[str] = mapped_column(String) # e.g., 'medical_reasoning', 'vision'
    
    # Model tracking
    provider: Mapped[AIModelProvider] = mapped_column(Enum(AIModelProvider), default=AIModelProvider.GEMINI)
    model_name: Mapped[str] = mapped_column(String)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metrics
    latency_ms: Mapped[float] = mapped_column(Float)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # Cost
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
