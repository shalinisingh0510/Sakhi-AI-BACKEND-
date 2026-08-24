"""SQLAlchemy ORM models for the Nutrition & Food Tracking domain (Phase 5).

Tables:
  foods               — canonical food database (Indian + international)
  food_serving_options — multiple serving representations per food
  nutrition_logs      — one record per user per date per meal type
  nutrition_log_items — individual food entries inside a log

Design notes:
  * Nutrition values stored per 100g canonical basis.
  * NutritionLogItem stores a snapshot of nutrition at logging time so that
    future food data corrections do NOT silently alter historical records.
  * diet_type on Food enables backend-side dietary compatibility checks.
  * search_aliases JSON column stores alternate names ("chapati", "phulka")
    for the same canonical food to power alias-aware search.
  * No AI, no calorie goals — purely deterministic data foundation.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ---------------------------------------------------------------------------
# Enumerations (stored as String columns — not DB-native enums for portability)
# ---------------------------------------------------------------------------

class FoodCategory:
    GRAINS = "GRAINS"
    PULSES = "PULSES"
    VEGETABLES = "VEGETABLES"
    FRUITS = "FRUITS"
    DAIRY = "DAIRY"
    EGGS = "EGGS"
    MEAT = "MEAT"
    SEAFOOD = "SEAFOOD"
    NUTS = "NUTS"
    SEEDS = "SEEDS"
    SNACKS = "SNACKS"
    BEVERAGES = "BEVERAGES"
    SWEETS = "SWEETS"
    PREPARED_MEALS = "PREPARED_MEALS"
    OILS_FATS = "OILS_FATS"
    SPICES = "SPICES"
    OTHER = "OTHER"


class DietType:
    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    EGGETARIAN = "EGGETARIAN"
    NON_VEGETARIAN = "NON_VEGETARIAN"


class DataQuality:
    VERIFIED = "VERIFIED"     # Sourced from USDA / IFCT / official databases
    ESTIMATED = "ESTIMATED"   # Approximated from similar foods
    DEMO = "DEMO"             # Seeded demo data — labelled clearly
    USER_GENERATED = "USER_GENERATED"


class MealType:
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACK = "SNACK"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Food (canonical food record)
# ---------------------------------------------------------------------------

class Food(Base):
    """Canonical food record in the Sakhi food database.

    All nutrition values are per 100g of the food.
    Users log food by selecting a serving option, which converts to grams.
    """

    __tablename__ = "foods"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Identity
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name_regional: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Classification
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    cuisine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    diet_type: Mapped[str] = mapped_column(String(30), nullable=False, default=DietType.VEGETARIAN)

    # Search aliases stored as JSON array: ["chapati", "phulka", "roti"]
    # Enables alias-aware search without duplicating food records
    search_aliases_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Core nutrition per 100g (required)
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sugar_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sodium_mg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Extended nutrition (nullable — added when reliable data exists)
    iron_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    calcium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    folate_mcg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vitamin_d_mcg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vitamin_b12_mcg: Mapped[float | None] = mapped_column(Float, nullable=True)
    potassium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Data provenance — IMPORTANT: never claim verified status without a real source
    data_quality: Mapped[str] = mapped_column(String(30), nullable=False, default=DataQuality.ESTIMATED)
    data_source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Soft-delete instead of hard-delete to preserve log item integrity
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_foods_name_en", "name_en"),
        Index("ix_foods_category", "category"),
        Index("ix_foods_diet_type", "diet_type"),
        Index("ix_foods_data_quality", "data_quality"),
        Index("ix_foods_is_active", "is_active"),
    )

    # -- Helper properties ---------------------------------------------------

    @property
    def search_aliases(self) -> list[str]:
        if not self.search_aliases_json:
            return []
        try:
            return json.loads(self.search_aliases_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @search_aliases.setter
    def search_aliases(self, value: list[str]) -> None:
        self.search_aliases_json = json.dumps(value or [])

    def all_search_terms(self) -> list[str]:
        """Return all names + aliases for search matching."""
        terms = [self.name_en]
        if self.name_hi:
            terms.append(self.name_hi)
        if self.name_regional:
            terms.append(self.name_regional)
        terms.extend(self.search_aliases)
        return [t.lower() for t in terms if t]


# ---------------------------------------------------------------------------
# FoodServingOption — multiple serving representations per food
# ---------------------------------------------------------------------------

class FoodServingOption(Base):
    """A single serving size option for a food.

    Example for Roti:
      - serving_label="1 roti", quantity_grams=40.0, is_default=True
      - serving_label="2 roti", quantity_grams=80.0
      - serving_label="100g",   quantity_grams=100.0

    The canonical basis is always 100g stored in the Food record.
    quantity_grams here defines how many grams this serving represents.
    """

    __tablename__ = "food_serving_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    food_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
    )

    serving_label: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_grams: Mapped[float] = mapped_column(Float, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_food_serving_options_food_id", "food_id"),
    )


# ---------------------------------------------------------------------------
# NutritionLog — one record per user × date × meal
# ---------------------------------------------------------------------------

class NutritionLog(Base):
    """Container for a single meal's food entries.

    Unique per (health_profile_id, log_date, meal_type) — prevents
    duplicate meal logs for the same date.
    """

    __tablename__ = "nutrition_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    health_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("health_profiles.id", ondelete="CASCADE"), nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "health_profile_id", "log_date", "meal_type",
            name="uq_nutrition_logs_profile_date_meal"
        ),
        Index("ix_nutrition_logs_health_profile_id", "health_profile_id"),
        Index("ix_nutrition_logs_log_date", "log_date"),
        Index("ix_nutrition_logs_profile_date", "health_profile_id", "log_date"),
    )


# ---------------------------------------------------------------------------
# NutritionLogItem — individual food entry inside a meal log
# ---------------------------------------------------------------------------

class NutritionLogItem(Base):
    """A single food entry within a NutritionLog (meal).

    CRITICAL DESIGN DECISION:
    Nutrition values (calories_snapshot, protein_snapshot, etc.) are stored
    at the time of logging — denormalized from the Food record. This ensures
    that future corrections to food database values do NOT silently corrupt
    historical calorie/nutrition data.

    quantity_grams is the resolved canonical quantity used for calculations.
    """

    __tablename__ = "nutrition_log_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nutrition_log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nutrition_logs.id", ondelete="CASCADE"), nullable=False
    )
    food_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False
    )
    serving_option_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("food_serving_options.id", ondelete="SET NULL"), nullable=True
    )

    # Quantity the user selected
    quantity_servings: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # Resolved canonical grams at log time (computed by NutritionEngine)
    quantity_grams: Mapped[float] = mapped_column(Float, nullable=False)

    # Nutrition snapshot — denormalized from Food at logging time
    # NEVER recalculate from current Food data — use these stored values
    calories_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fiber_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Food name snapshot — so display doesn't break if food is deactivated
    food_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_nutrition_log_items_nutrition_log_id", "nutrition_log_id"),
        Index("ix_nutrition_log_items_food_id", "food_id"),
    )
