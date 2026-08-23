"""Transaction management utilities for SQLAlchemy sessions.

Provides a context-manager that commits on success and rolls back on
failure, keeping transaction handling out of individual service methods.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

from sqlalchemy.orm import Session


@contextmanager
def transactional(session: Session) -> Generator[Session, None, None]:
    """Execute a block inside a database transaction.

    Commits automatically if the block completes without exception;
    rolls back otherwise.

    Example::

        with transactional(db) as s:
            s.add(record)
    """
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
