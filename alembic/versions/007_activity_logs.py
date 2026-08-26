"""007_activity_logs — Create Activity and Energy tables (Phase 6/7).

Tables created:
  activity_logs         — one record per activity logged by the user

Columns added:
  health_profiles.biological_sex — required for BMR calculations

Revision: 007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add biological_sex to health_profiles
    op.add_column(
        "health_profiles",
        sa.Column("biological_sex", sa.String(length=20), nullable=True),
    )

    # 2. Create activity_logs
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("health_profile_id", sa.String(length=36), nullable=False),
        sa.Column("cycle_id", sa.String(length=36), nullable=True),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.String(length=20), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("estimated_calories_burned", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("calculation_method", sa.String(length=100), nullable=True),
        sa.Column("algorithm_version", sa.String(length=20), nullable=True),
        sa.Column("external_source", sa.String(length=100), nullable=True),
        sa.Column("external_record_id", sa.String(length=200), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["health_profile_id"],
            ["health_profiles.id"],
            name="fk_activity_logs_profile_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    
    op.create_index(
        "ix_activity_logs_health_profile_id",
        "activity_logs",
        ["health_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_logs_date",
        "activity_logs",
        ["activity_date"],
        unique=False,
    )
    op.create_index(
        "ix_activity_logs_profile_date",
        "activity_logs",
        ["health_profile_id", "activity_date"],
        unique=False,
    )
    op.create_index(
        "ix_activity_logs_cycle_id",
        "activity_logs",
        ["cycle_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_activity_logs_cycle_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_profile_date", table_name="activity_logs")
    op.drop_index("ix_activity_logs_date", table_name="activity_logs")
    op.drop_index("ix_activity_logs_health_profile_id", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_column("health_profiles", "biological_sex")
