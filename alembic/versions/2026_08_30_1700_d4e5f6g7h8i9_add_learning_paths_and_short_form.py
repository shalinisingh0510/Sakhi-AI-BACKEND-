"""Add learning paths and short form

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-08-30 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add is_short_form to learning_content
    op.add_column('learning_content', sa.Column('is_short_form', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    # Create learning_paths table
    op.create_table('learning_paths',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('topic_id', sa.String(length=36), nullable=False),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('audience', sa.String(length=10), server_default='ALL', nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_featured', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_learning_paths_audience', 'learning_paths', ['audience'], unique=False)
    op.create_index('ix_learning_paths_language', 'learning_paths', ['language'], unique=False)
    op.create_index('ix_learning_paths_slug', 'learning_paths', ['slug'], unique=False)
    op.create_index('ix_learning_paths_status', 'learning_paths', ['status'], unique=False)
    op.create_index('ix_learning_paths_topic_id', 'learning_paths', ['topic_id'], unique=False)

    # Create learning_modules table
    op.create_table('learning_modules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('path_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_learning_modules_path_id', 'learning_modules', ['path_id'], unique=False)

    # Create learning_module_items table
    op.create_table('learning_module_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('module_id', sa.String(length=36), nullable=False),
        sa.Column('content_id', sa.String(length=36), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['learning_content.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_id'], ['learning_modules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('module_id', 'content_id', name='uq_module_content_item')
    )
    op.create_index('ix_learning_module_items_content_id', 'learning_module_items', ['content_id'], unique=False)
    op.create_index('ix_learning_module_items_module_id', 'learning_module_items', ['module_id'], unique=False)


def downgrade() -> None:
    op.drop_table('learning_module_items')
    op.drop_table('learning_modules')
    op.drop_table('learning_paths')
    op.drop_column('learning_content', 'is_short_form')
