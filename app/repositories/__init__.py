"""Repository layer for Sakhi AI.

Provides a base repository class with common CRUD operations for
SQLAlchemy models, and re-exports concrete repositories.
"""

from app.repositories.base import BaseRepository

__all__ = ["BaseRepository"]
