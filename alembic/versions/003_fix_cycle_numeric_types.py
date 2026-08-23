"""Alembic migration 003 — fix menstrual_cycle string types to int.

Revision ID: 003_fix_cycle_numeric_types
Revises: 002_menstrual_cycle
Create Date: 2026-08-23

Downgrade notes:
  * Downgrade converts them back to strings.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_fix_cycle_numeric_types"
down_revision: Union[str, None] = "002_menstrual_cycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use USING to safely cast strings to integers if data already exists
    op.execute(
        "ALTER TABLE menstrual_cycles ALTER COLUMN cycle_length_days TYPE integer USING cycle_length_days::integer"
    )
    op.execute(
        "ALTER TABLE menstrual_cycles ALTER COLUMN period_duration_days TYPE integer USING period_duration_days::integer"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE menstrual_cycles ALTER COLUMN cycle_length_days TYPE varchar(10) USING cycle_length_days::varchar"
    )
    op.execute(
        "ALTER TABLE menstrual_cycles ALTER COLUMN period_duration_days TYPE varchar(10) USING period_duration_days::varchar"
    )
