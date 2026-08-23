"""FastAPI dependency for SQLAlchemy database sessions.

Provides a ``get_db`` generator that yields a ``Session`` and ensures
proper cleanup.  Follows the existing project pattern of injecting
services via ``Depends()``.

Usage in an endpoint::

    from app.db.dependencies import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import get_session_factory


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, closing it after the request."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
