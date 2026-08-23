"""Base repository providing common CRUD operations.

Concrete repositories (e.g. ``HealthProfileRepository``) should
inherit from ``BaseRepository[Model]`` and add domain-specific queries.

The base class is intentionally thin — only operations that virtually
every entity needs.  Domain logic belongs in the service layer, not
here.
"""

from __future__ import annotations

import logging
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)
logger = logging.getLogger("sakhi.repository")


class BaseRepository(Generic[ModelT]):
    """Generic CRUD repository for SQLAlchemy models."""

    def __init__(self, session: Session, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    # -- Read -----------------------------------------------------------------

    def get_by_id(self, record_id: str) -> ModelT | None:
        """Fetch a single record by primary key."""
        return self._session.get(self._model_class, record_id)

    def list_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Return a paginated list of records."""
        return (
            self._session.query(self._model_class)
            .limit(limit)
            .offset(offset)
            .all()
        )

    # -- Write ----------------------------------------------------------------

    def add(self, instance: ModelT) -> ModelT:
        """Add a new record to the session (caller must commit)."""
        self._session.add(instance)
        self._session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        """Remove a record from the session (caller must commit)."""
        self._session.delete(instance)
        self._session.flush()
