"""Alembic migration 005 — add explicit foreign keys to wellness tables.

Revision ID: 005_wellness_foreign_keys
Revises: 004_symptoms_mood_energy
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_wellness_foreign_keys"
down_revision: Union[str, None] = "004_symptoms_mood_energy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add foreign keys for symptom_logs
    op.create_foreign_key(
        "fk_symptom_logs_health_profile_id",
        "symptom_logs",
        "health_profiles",
        ["health_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_symptom_logs_cycle_id",
        "symptom_logs",
        "menstrual_cycles",
        ["cycle_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add foreign keys for mood_logs
    op.create_foreign_key(
        "fk_mood_logs_health_profile_id",
        "mood_logs",
        "health_profiles",
        ["health_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_mood_logs_cycle_id",
        "mood_logs",
        "menstrual_cycles",
        ["cycle_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add foreign keys for energy_logs
    op.create_foreign_key(
        "fk_energy_logs_health_profile_id",
        "energy_logs",
        "health_profiles",
        ["health_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_energy_logs_cycle_id",
        "energy_logs",
        "menstrual_cycles",
        ["cycle_id"],
        ["id"],
        ondelete="SET NULL",
    )

def downgrade() -> None:
    op.drop_constraint("fk_energy_logs_cycle_id", "energy_logs", type_="foreignkey")
    op.drop_constraint("fk_energy_logs_health_profile_id", "energy_logs", type_="foreignkey")
    
    op.drop_constraint("fk_mood_logs_cycle_id", "mood_logs", type_="foreignkey")
    op.drop_constraint("fk_mood_logs_health_profile_id", "mood_logs", type_="foreignkey")
    
    op.drop_constraint("fk_symptom_logs_cycle_id", "symptom_logs", type_="foreignkey")
    op.drop_constraint("fk_symptom_logs_health_profile_id", "symptom_logs", type_="foreignkey")
