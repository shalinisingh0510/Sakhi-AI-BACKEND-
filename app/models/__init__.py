"""SQLAlchemy ORM models for Sakhi AI.

Import all model modules here so that ``Base.metadata`` discovers every
table when Alembic runs ``target_metadata = Base.metadata``.

**Important**: Existing tables (users, conversations, etc.) are still
managed by the ``psycopg``-based store classes.  Only *new* domain
models (health, wellness, etc.) should be added here.
"""

from app.db.base import Base  # noqa: F401 — re-export for Alembic

# Future model imports — uncomment as models are created:
# from app.models.health import HealthEvent  # noqa: F401
