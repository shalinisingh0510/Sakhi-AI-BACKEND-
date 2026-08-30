"""Add Learning Content System tables.

Revision ID: a1b2c3d4e5f6
Revises: 0774cacc63a8
Create Date: 2026-08-29 12:00:00.000000

Creates:
  - learning_content
  - learning_progress

NOTE: media_file_id and thumbnail_file_id reference media_files.id which is
managed by psycopg (not SQLAlchemy/Alembic), so we do NOT create foreign-key
constraints for them — they are plain text columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0774cacc63a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_content",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("media_url", sa.String(length=500), nullable=True),
        # References media_files.id — plain String, no FK constraint (cross-ORM)
        sa.Column("media_file_id", sa.String(length=64), nullable=True),
        sa.Column("thumbnail_file_id", sa.String(length=64), nullable=True),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("author_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_learning_content_status", "learning_content", ["status"])
    op.create_index("ix_learning_content_category", "learning_content", ["category"])
    op.create_index("ix_learning_content_content_type", "learning_content", ["content_type"])
    op.create_index("ix_learning_content_created_at", "learning_content", ["created_at"])

    op.create_table(
        "learning_progress",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "watch_time_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "progress_percent", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["learning_content.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "content_id"),
    )

    op.create_index("ix_learning_progress_user_id", "learning_progress", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_progress_user_id", table_name="learning_progress")
    op.drop_table("learning_progress")
    op.drop_index("ix_learning_content_created_at", table_name="learning_content")
    op.drop_index("ix_learning_content_content_type", table_name="learning_content")
    op.drop_index("ix_learning_content_category", table_name="learning_content")
    op.drop_index("ix_learning_content_status", table_name="learning_content")
    op.drop_table("learning_content")
