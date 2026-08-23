"""SQLAlchemy engine and session factory for Sakhi AI.

Reads ``SAKHI_DATABASE_URL`` (or ``database_url`` on the Settings object)
and creates a synchronous engine compatible with Neon serverless PostgreSQL.

Usage from FastAPI dependencies::

    from app.db.dependencies import get_db
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger("sakhi.db")


def _build_engine(database_url: str) -> "Engine":
    """Create a SQLAlchemy engine with Neon-compatible defaults.

    * ``pool_pre_ping=True`` — handles Neon's connection recycling.
    * ``pool_size`` kept small for serverless PostgreSQL.
    * SSL is expected to be configured via the connection string
      (e.g. ``?sslmode=require``).
    """
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    connect_args: dict = {}

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        connect_args=connect_args,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
        logger.debug("SQLAlchemy connection established.")

    return engine


# ---------------------------------------------------------------------------
# Module-level singletons (lazy-initialised via ``init_db``)
# ---------------------------------------------------------------------------

_engine: "Engine | None" = None
_SessionLocal: sessionmaker[Session] | None = None


def init_db(database_url: str) -> None:
    """Initialise the module-level engine and session factory.

    Call once during application startup (e.g. inside ``create_app``).
    """
    global _engine, _SessionLocal  # noqa: PLW0603
    _engine = _build_engine(database_url)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    logger.info("SQLAlchemy engine initialised.")


def get_engine() -> "Engine":
    """Return the current engine.  Raises if ``init_db`` was not called."""
    if _engine is None:
        raise RuntimeError(
            "SQLAlchemy engine not initialised. Call init_db() during app startup."
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the current session factory."""
    if _SessionLocal is None:
        raise RuntimeError(
            "SQLAlchemy session factory not initialised. Call init_db() during app startup."
        )
    return _SessionLocal
