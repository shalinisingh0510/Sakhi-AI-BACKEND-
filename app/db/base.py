"""SQLAlchemy declarative base for Sakhi AI.

All ORM models inherit from ``Base``.  Alembic discovers tables via
``Base.metadata``, so every model module must be imported before
running migrations (see ``app/models/__init__.py``).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Application-wide SQLAlchemy declarative base.

    New domain models (health, wellness, etc.) should subclass this.
    Existing ``psycopg``-managed tables are **not** registered here —
    they continue to be handled by their respective store classes until
    a future migration phase.
    """

    pass
