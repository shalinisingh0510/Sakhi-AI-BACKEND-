"""Alembic migration 002 — create menstrual cycle tables.

Revision ID: 002_menstrual_cycle
Revises: 001_health_profile
Create Date: 2026-08-23

Tables created:
  period_logs       — raw user-entered period start/end data.
  menstrual_cycles  — system-derived cycle records.
  cycle_predictions — calculated future estimates.

Downgrade notes:
  * Downgrade drops all three tables permanently.
  * NEVER run against production without a data-backup and data-purge review.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_menstrual_cycle"
down_revision: Union[str, None] = "001_health_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # period_logs — raw user-entered period data
    # ------------------------------------------------------------------
    op.create_table(
        "period_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("flow", sa.String(10), nullable=False, server_default="UNKNOWN"),
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
        sa.UniqueConstraint(
            "health_profile_id",
            "start_date",
            name="uq_period_logs_profile_start",
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_period_logs_end_after_start",
        ),
    )
    op.create_index(
        "ix_period_logs_health_profile_id", "period_logs", ["health_profile_id"]
    )
    op.create_index("ix_period_logs_start_date", "period_logs", ["start_date"])

    # ------------------------------------------------------------------
    # menstrual_cycles — system-derived cycle records
    # ------------------------------------------------------------------
    op.create_table(
        "menstrual_cycles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("cycle_start_date", sa.Date, nullable=False),
        sa.Column("cycle_end_date", sa.Date, nullable=True),
        sa.Column("cycle_length_days", sa.String(10), nullable=True),
        sa.Column("period_duration_days", sa.String(10), nullable=True),
        sa.Column(
            "is_complete", sa.Boolean, nullable=False, server_default=sa.false()
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
        sa.UniqueConstraint(
            "health_profile_id",
            "cycle_start_date",
            name="uq_menstrual_cycles_profile_start",
        ),
    )
    op.create_index(
        "ix_menstrual_cycles_health_profile_id",
        "menstrual_cycles",
        ["health_profile_id"],
    )
    op.create_index(
        "ix_menstrual_cycles_cycle_start_date",
        "menstrual_cycles",
        ["cycle_start_date"],
    )

    # ------------------------------------------------------------------
    # cycle_predictions — calculated future estimates
    # ------------------------------------------------------------------
    op.create_table(
        "cycle_predictions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36), nullable=False),
        sa.Column("reference_cycle_id", sa.String(36), nullable=True),
        sa.Column("prediction_type", sa.String(30), nullable=False),
        sa.Column("predicted_start_date", sa.Date, nullable=False),
        sa.Column("predicted_end_date", sa.Date, nullable=True),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("calculation_method", sa.String(80), nullable=False),
        sa.Column(
            "algorithm_version",
            sa.String(20),
            nullable=False,
            server_default="cycle-v1",
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cycle_predictions_health_profile_id",
        "cycle_predictions",
        ["health_profile_id"],
    )
    op.create_index(
        "ix_cycle_predictions_type", "cycle_predictions", ["prediction_type"]
    )
    op.create_index(
        "ix_cycle_predictions_predicted_start",
        "cycle_predictions",
        ["predicted_start_date"],
    )


def downgrade() -> None:
    # WARNING: Drops all cycle prediction, cycle, and period data irreversibly.
    op.drop_index(
        "ix_cycle_predictions_predicted_start", table_name="cycle_predictions"
    )
    op.drop_index("ix_cycle_predictions_type", table_name="cycle_predictions")
    op.drop_index(
        "ix_cycle_predictions_health_profile_id", table_name="cycle_predictions"
    )
    op.drop_table("cycle_predictions")

    op.drop_index(
        "ix_menstrual_cycles_cycle_start_date", table_name="menstrual_cycles"
    )
    op.drop_index(
        "ix_menstrual_cycles_health_profile_id", table_name="menstrual_cycles"
    )
    op.drop_table("menstrual_cycles")

    op.drop_index("ix_period_logs_start_date", table_name="period_logs")
    op.drop_index("ix_period_logs_health_profile_id", table_name="period_logs")
    op.drop_table("period_logs")
