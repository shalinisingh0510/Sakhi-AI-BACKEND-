"""006_nutrition_tables — Create Nutrition & Food Tracking tables (Phase 5).

Tables created:
  foods                 — canonical food database
  food_serving_options  — multiple serving representations per food
  nutrition_logs        — one record per user × date × meal type
  nutrition_log_items   — individual food entries inside a meal log

Rollback:
  All tables are dropped in reverse dependency order.
  Existing Phase 0-4 data is untouched.

Revision: 006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # foods
    # ------------------------------------------------------------------
    op.create_table(
        "foods",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_hi", sa.String(200), nullable=True),
        sa.Column("name_regional", sa.String(200), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("cuisine", sa.String(100), nullable=True),
        sa.Column("diet_type", sa.String(30), nullable=False, server_default="VEGETARIAN"),
        sa.Column("search_aliases_json", sa.Text, nullable=True),
        # Core nutrition per 100g
        sa.Column("calories_per_100g", sa.Float, nullable=False),
        sa.Column("protein_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("carbs_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("fat_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("fiber_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("sugar_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("sodium_mg", sa.Float, nullable=False, server_default="0"),
        # Extended nutrition (nullable)
        sa.Column("iron_mg", sa.Float, nullable=True),
        sa.Column("calcium_mg", sa.Float, nullable=True),
        sa.Column("folate_mcg", sa.Float, nullable=True),
        sa.Column("vitamin_d_mcg", sa.Float, nullable=True),
        sa.Column("vitamin_b12_mcg", sa.Float, nullable=True),
        sa.Column("potassium_mg", sa.Float, nullable=True),
        # Provenance
        sa.Column("data_quality", sa.String(30), nullable=False, server_default="ESTIMATED"),
        sa.Column("data_source", sa.String(500), nullable=True),
        sa.Column("data_version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    op.create_index("ix_foods_name_en", "foods", ["name_en"])
    op.create_index("ix_foods_category", "foods", ["category"])
    op.create_index("ix_foods_diet_type", "foods", ["diet_type"])
    op.create_index("ix_foods_data_quality", "foods", ["data_quality"])
    op.create_index("ix_foods_is_active", "foods", ["is_active"])

    # ------------------------------------------------------------------
    # food_serving_options
    # ------------------------------------------------------------------
    op.create_table(
        "food_serving_options",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "food_id",
            sa.String(36),
            sa.ForeignKey("foods.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("serving_label", sa.String(100), nullable=False),
        sa.Column("quantity_grams", sa.Float, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_food_serving_options_food_id", "food_serving_options", ["food_id"]
    )

    # ------------------------------------------------------------------
    # nutrition_logs
    # ------------------------------------------------------------------
    op.create_table(
        "nutrition_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "health_profile_id",
            sa.String(36),
            sa.ForeignKey("health_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
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
            "log_date",
            "meal_type",
            name="uq_nutrition_logs_profile_date_meal",
        ),
    )
    op.create_index(
        "ix_nutrition_logs_health_profile_id", "nutrition_logs", ["health_profile_id"]
    )
    op.create_index("ix_nutrition_logs_log_date", "nutrition_logs", ["log_date"])
    op.create_index(
        "ix_nutrition_logs_profile_date",
        "nutrition_logs",
        ["health_profile_id", "log_date"],
    )

    # ------------------------------------------------------------------
    # nutrition_log_items
    # ------------------------------------------------------------------
    op.create_table(
        "nutrition_log_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "nutrition_log_id",
            sa.String(36),
            sa.ForeignKey("nutrition_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            sa.String(36),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "serving_option_id",
            sa.String(36),
            sa.ForeignKey("food_serving_options.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity_servings", sa.Float, nullable=False, server_default="1"),
        sa.Column("quantity_grams", sa.Float, nullable=False),
        # Nutrition snapshot (denormalized at log time)
        sa.Column("calories_snapshot", sa.Float, nullable=False, server_default="0"),
        sa.Column("protein_snapshot", sa.Float, nullable=False, server_default="0"),
        sa.Column("carbs_snapshot", sa.Float, nullable=False, server_default="0"),
        sa.Column("fat_snapshot", sa.Float, nullable=False, server_default="0"),
        sa.Column("fiber_snapshot", sa.Float, nullable=False, server_default="0"),
        # Food name snapshot for display integrity
        sa.Column("food_name_snapshot", sa.String(200), nullable=False),
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
    op.create_index(
        "ix_nutrition_log_items_nutrition_log_id",
        "nutrition_log_items",
        ["nutrition_log_id"],
    )
    op.create_index(
        "ix_nutrition_log_items_food_id", "nutrition_log_items", ["food_id"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("nutrition_log_items")
    op.drop_table("nutrition_logs")
    op.drop_table("food_serving_options")
    op.drop_table("foods")
