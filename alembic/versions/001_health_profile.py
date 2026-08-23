"""add health_profile and health_conditions tables

Revision ID: 001_health_profile
Revises: 
Create Date: 2026-08-23

Tables:
  health_profiles   — one per user, stores wellness preferences and DOB.
  health_conditions — self-reported conditions (one-to-many with users).

Downgrade notes:
  * Downgrade drops both tables permanently.
  * Never run downgrade against production without a data backup and
    a deliberate data-purge review.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_health_profile"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "health_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=False),
        sa.Column("height_cm", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("activity_level", sa.String(20), nullable=False, server_default="SEDENTARY"),
        sa.Column("diet_type", sa.String(20), nullable=False, server_default="OTHER"),
        sa.Column("food_allergies_json", sa.Text, nullable=True),
        sa.Column("dietary_restrictions_json", sa.Text, nullable=True),
        sa.Column("cycle_tracking_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("nutrition_tracking_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("activity_tracking_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "ai_health_personalization_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),  # IMPORTANT: opt-in only
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_health_profiles_user_id"),
    )
    op.create_index("ix_health_profiles_user_id", "health_profiles", ["user_id"])

    op.create_table(
        "health_conditions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("condition_code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="self_reported"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_health_conditions_user_id", "health_conditions", ["user_id"])
    op.create_index(
        "ix_health_conditions_condition_code", "health_conditions", ["condition_code"]
    )


def downgrade() -> None:
    # WARNING: Drops all user health data irreversibly.
    # Never run against production without data backup.
    op.drop_index("ix_health_conditions_condition_code", table_name="health_conditions")
    op.drop_index("ix_health_conditions_user_id", table_name="health_conditions")
    op.drop_table("health_conditions")

    op.drop_index("ix_health_profiles_user_id", table_name="health_profiles")
    op.drop_table("health_profiles")
