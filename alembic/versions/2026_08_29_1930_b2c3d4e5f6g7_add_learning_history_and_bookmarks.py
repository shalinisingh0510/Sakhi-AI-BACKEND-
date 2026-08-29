"""Add learning history and bookmarks.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29 19:30:00.000000

Creates:
  - learning_bookmarks table
Modifies:
  - adds view_count to learning_progress
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add view_count to learning_progress
    op.add_column('learning_progress', sa.Column('view_count', sa.Integer(), server_default='0', nullable=False))

    # Create learning_bookmarks
    op.create_table(
        'learning_bookmarks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('content_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['learning_content.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'content_id', name='uq_user_content_bookmark')
    )
    op.create_index('ix_learning_bookmarks_user_id', 'learning_bookmarks', ['user_id'], unique=False)
    op.create_index('ix_learning_bookmarks_content_id', 'learning_bookmarks', ['content_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_learning_bookmarks_content_id', table_name='learning_bookmarks')
    op.drop_index('ix_learning_bookmarks_user_id', table_name='learning_bookmarks')
    op.drop_table('learning_bookmarks')

    op.drop_column('learning_progress', 'view_count')
