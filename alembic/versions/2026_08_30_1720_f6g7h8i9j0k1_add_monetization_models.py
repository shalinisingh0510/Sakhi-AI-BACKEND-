"""add_monetization_models

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-08-30 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ad_placement_configs
    op.create_table(
        'ad_placement_configs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('placement', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='ADSENSE'),
        sa.Column('is_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('audience_policy', sa.String(length=20), server_default='ALL', nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('placement')
    )
    op.create_index('ix_ad_placement_configs_placement', 'ad_placement_configs', ['placement'], unique=False)

    # 2. Create sponsors
    op.create_table(
        'sponsors',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sponsors_status', 'sponsors', ['status'], unique=False)

    # 3. Create affiliate_partners
    op.create_table(
        'affiliate_partners',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_affiliate_partners_status', 'affiliate_partners', ['status'], unique=False)

    # 4. Create affiliate_products
    op.create_table(
        'affiliate_products',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('partner_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('disclosure_text', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['partner_id'], ['affiliate_partners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_affiliate_products_partner_id', 'affiliate_products', ['partner_id'], unique=False)
    op.create_index('ix_affiliate_products_status', 'affiliate_products', ['status'], unique=False)

    # 5. Add sponsor_id to learning_content
    op.add_column('learning_content', sa.Column('sponsor_id', sa.String(length=36), nullable=True))
    op.create_index('ix_learning_content_sponsor_id', 'learning_content', ['sponsor_id'], unique=False)
    op.create_foreign_key(None, 'learning_content', 'sponsors', ['sponsor_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # 5. Remove sponsor_id from learning_content
    op.drop_constraint(None, 'learning_content', type_='foreignkey')
    op.drop_index('ix_learning_content_sponsor_id', table_name='learning_content')
    op.drop_column('learning_content', 'sponsor_id')

    # 4. Drop affiliate_products
    op.drop_index('ix_affiliate_products_status', table_name='affiliate_products')
    op.drop_index('ix_affiliate_products_partner_id', table_name='affiliate_products')
    op.drop_table('affiliate_products')

    # 3. Drop affiliate_partners
    op.drop_index('ix_affiliate_partners_status', table_name='affiliate_partners')
    op.drop_table('affiliate_partners')

    # 2. Drop sponsors
    op.drop_index('ix_sponsors_status', table_name='sponsors')
    op.drop_table('sponsors')

    # 1. Drop ad_placement_configs
    op.drop_index('ix_ad_placement_configs_placement', table_name='ad_placement_configs')
    op.drop_table('ad_placement_configs')
