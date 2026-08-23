"""Alembic migration 004 — create symptom, mood, and energy tables.

Revision ID: 004_symptoms_mood_energy
Revises: 003_fix_cycle_numeric_types
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_symptoms_mood_energy"
down_revision: Union[str, None] = "003_fix_cycle_numeric_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # symptom_logs
    # ------------------------------------------------------------------
    op.create_table(
        "symptom_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("cycle_id", sa.String(36), nullable=True),
        sa.Column("cycle_day", sa.Integer, nullable=True),
        sa.Column("symptom_code", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
    op.create_index("ix_symptom_logs_health_profile_id", "symptom_logs", ["health_profile_id"])
    op.create_index("ix_symptom_logs_start_date", "symptom_logs", ["start_date"])
    op.create_index("ix_symptom_logs_symptom_code", "symptom_logs", ["symptom_code"])
    op.create_index("ix_symptom_logs_cycle_id", "symptom_logs", ["cycle_id"])

    # ------------------------------------------------------------------
    # mood_logs
    # ------------------------------------------------------------------
    op.create_table(
        "mood_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("mood_code", sa.String(50), nullable=False),
        sa.Column("intensity", sa.String(20), nullable=False),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("cycle_id", sa.String(36), nullable=True),
        sa.Column("cycle_day", sa.Integer, nullable=True),
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
        sa.UniqueConstraint("health_profile_id", "log_date", name="uq_mood_logs_profile_date")
    )
    op.create_index("ix_mood_logs_health_profile_id", "mood_logs", ["health_profile_id"])
    op.create_index("ix_mood_logs_log_date", "mood_logs", ["log_date"])
    op.create_index("ix_mood_logs_cycle_id", "mood_logs", ["cycle_id"])

    # ------------------------------------------------------------------
    # energy_logs
    # ------------------------------------------------------------------
    op.create_table(
        "energy_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("energy_level", sa.String(50), nullable=False),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("cycle_id", sa.String(36), nullable=True),
        sa.Column("cycle_day", sa.Integer, nullable=True),
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
        sa.UniqueConstraint("health_profile_id", "log_date", name="uq_energy_logs_profile_date")
    )
    op.create_index("ix_energy_logs_health_profile_id", "energy_logs", ["health_profile_id"])
    op.create_index("ix_energy_logs_log_date", "energy_logs", ["log_date"])
    op.create_index("ix_energy_logs_cycle_id", "energy_logs", ["cycle_id"])


def downgrade() -> None:
    op.drop_table("energy_logs")
    op.drop_table("mood_logs")
    op.drop_table("symptom_logs")
