"""Repository layer for Sakhi AI.

Provides a base repository class with common CRUD operations for
SQLAlchemy models, and re-exports concrete repositories.
"""

from app.repositories.base import BaseRepository
from app.repositories.health import HealthConditionRepository, HealthProfileRepository

__all__ = ["BaseRepository", "HealthConditionRepository", "HealthProfileRepository"]
