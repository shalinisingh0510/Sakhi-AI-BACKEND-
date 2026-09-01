"""add_research_sources

Revision ID: a1b2c3d4e5f6_rs
Revises: f6g7h8i9j0k1
Create Date: 2026-09-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6_rs'
down_revision = 'f6g7h8i9j0k1'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'research_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('canonical_url', sa.String(length=2048), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('publisher', sa.String(length=255), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('accessed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('extracted_facts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('content_hash', sa.String(length=128), nullable=True),
        sa.Column('related_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_sources_domain', 'research_sources', ['domain'], unique=False)
    op.create_index('ix_research_sources_canonical_url', 'research_sources', ['canonical_url'], unique=False)
    op.create_index('ix_research_sources_content_hash', 'research_sources', ['content_hash'], unique=False)

def downgrade():
    op.drop_index('ix_research_sources_content_hash', table_name='research_sources')
    op.drop_index('ix_research_sources_canonical_url', table_name='research_sources')
    op.drop_index('ix_research_sources_domain', table_name='research_sources')
    op.drop_table('research_sources')
