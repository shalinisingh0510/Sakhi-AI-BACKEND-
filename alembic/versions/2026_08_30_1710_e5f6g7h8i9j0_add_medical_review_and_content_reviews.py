"""add medical review and content reviews

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-08-30 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add columns to learning_content
    op.add_column('learning_content', sa.Column('medical_review_status', sa.String(length=20), server_default='NOT_REVIEWED', nullable=False))
    op.add_column('learning_content', sa.Column('medical_reviewer_id', sa.String(length=64), nullable=True))
    op.add_column('learning_content', sa.Column('medical_reviewed_at', sa.DateTime(), nullable=True))
    
    op.create_index('ix_learning_content_medical_review', 'learning_content', ['medical_review_status'], unique=False)

    # 2. Create content_reviews table
    op.create_table(
        'content_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_id', sa.String(length=36), nullable=False),
        sa.Column('reviewer_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['learning_content.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_content_reviews_content_id', 'content_reviews', ['content_id'], unique=False)
    op.create_index('ix_content_reviews_reviewer_id', 'content_reviews', ['reviewer_id'], unique=False)


def downgrade():
    # 1. Drop content_reviews table
    op.drop_index('ix_content_reviews_reviewer_id', table_name='content_reviews')
    op.drop_index('ix_content_reviews_content_id', table_name='content_reviews')
    op.drop_table('content_reviews')

    # 2. Drop columns from learning_content
    op.drop_index('ix_learning_content_medical_review', table_name='learning_content')
    op.drop_column('learning_content', 'medical_reviewed_at')
    op.drop_column('learning_content', 'medical_reviewer_id')
    op.drop_column('learning_content', 'medical_review_status')
