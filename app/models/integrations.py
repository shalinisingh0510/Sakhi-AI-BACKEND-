from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.db.base import Base

class ProviderType(str, enum.Enum):
    GOOGLE_HEALTH_CONNECT = "GOOGLE_HEALTH_CONNECT"
    APPLE_HEALTH = "APPLE_HEALTH"
    SAMSUNG_HEALTH = "SAMSUNG_HEALTH"
    WEARABLE = "WEARABLE"

class ConnectionStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    EXPIRED = "EXPIRED"

class SyncStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class HealthProviderConnection(Base):
    """
    Tracks the user's OAuth/Integration connection to an external health data provider.
    """
    __tablename__ = "health_provider_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus), default=ConnectionStatus.CONNECTED)
    
    scopes: Mapped[List[str]] = mapped_column(JSONB, default=list) # e.g. ["STEPS", "DISTANCE", "ACTIVE_ENERGY"]
    
    # Store encrypted/secure tokens (mock implementation)
    provider_user_id: Mapped[Optional[str]] = mapped_column(String)
    
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    sync_logs: Mapped[List["ExternalSyncLog"]] = relationship("ExternalSyncLog", back_populates="connection")


class ExternalSyncLog(Base):
    """
    Audit log for data synchronization runs to prevent downloading the entire history every time.
    """
    __tablename__ = "external_sync_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("health_provider_connections.id"), nullable=False)
    
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), nullable=False)
    
    records_imported: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    
    error_message: Mapped[Optional[str]] = mapped_column(String)
    
    sync_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    sync_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    connection: Mapped["HealthProviderConnection"] = relationship("HealthProviderConnection", back_populates="sync_logs")
