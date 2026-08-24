"""Pydantic schemas for Nutrition & Food Tracking (Phase 5).

These schemas define the API contract for:
  - Food search and detail
  - Food serving options
  - Nutrition log creation / update / response
  - Daily nutrition summary

Design notes:
  * Allergen warnings are computed backend-side from profile.food_allergies.
  * Diet compatibility is computed backend-side from profile.diet_type.
  * No calorie goals or targets in Phase 5.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FoodCategory(StrEnum):
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


class DietType(StrEnum):
    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    EGGETARIAN = "EGGETARIAN"
    NON_VEGETARIAN = "NON_VEGETARIAN"


class DataQuality(StrEnum):
    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    DEMO = "DEMO"
    USER_GENERATED = "USER_GENERATED"


class MealType(StrEnum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACK = "SNACK"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Nutrition Facts (reusable value object)
# ---------------------------------------------------------------------------


class NutritionFacts(BaseModel):
    """Nutrition totals — informational only, NOT a target or recommendation."""

    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0


# ---------------------------------------------------------------------------
# Food Serving Option
# ---------------------------------------------------------------------------


class FoodServingOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    food_id: str
    serving_label: str
    quantity_grams: float
    is_default: bool
    sort_order: int


# ---------------------------------------------------------------------------
# Food
# ---------------------------------------------------------------------------


class FoodResponse(BaseModel):
    """Full food detail including serving options and user-specific flags."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name_en: str
    name_hi: Optional[str]
    name_regional: Optional[str]
    category: str
    cuisine: Optional[str]
    diet_type: str
    search_aliases: list[str] = []

    # Nutrition per 100g
    calories_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    sugar_g: float
    sodium_mg: float

    # Optional extended nutrition
    iron_mg: Optional[float]
    calcium_mg: Optional[float]
    folate_mcg: Optional[float]

    data_quality: str
    data_source: Optional[str]
    is_active: bool

    # Serving options for this food
    serving_options: list[FoodServingOptionResponse] = []

    # User-specific flags computed at request time
    allergen_warnings: list[str] = Field(
        default_factory=list,
        description="Allergens from user profile that may be present in this food.",
    )
    is_diet_compatible: bool = Field(
        default=True,
        description="Whether this food is compatible with the user's diet_type preference.",
    )


class FoodSearchResultResponse(BaseModel):
    """Lightweight food result for search listings."""

    id: str
    name_en: str
    name_hi: Optional[str]
    category: str
    diet_type: str
    calories_per_100g: float
    data_quality: str
    # Default serving for quick display
    default_serving_label: Optional[str]
    default_serving_grams: Optional[float]
    # User flags
    allergen_warnings: list[str] = []
    is_diet_compatible: bool = True


class FoodSearchResponse(BaseModel):
    """Paginated food search results."""

    results: list[FoodSearchResultResponse]
    total_count: int
    page: int
    page_size: int
    query: Optional[str]


# ---------------------------------------------------------------------------
# Nutrition Log Item (individual food in a meal)
# ---------------------------------------------------------------------------


class NutritionLogItemCreate(BaseModel):
    """Create a food entry within a meal log."""

    food_id: str
    serving_option_id: Optional[str] = None
    quantity_servings: float = Field(default=1.0, gt=0, le=100)
    # Override quantity in grams (if user picks "100g" manually)
    quantity_grams_override: Optional[float] = Field(default=None, gt=0)
    meal_type: MealType
    log_date: date


class NutritionLogItemUpdate(BaseModel):
    """Update an existing food log item."""

    serving_option_id: Optional[str] = None
    quantity_servings: Optional[float] = Field(default=None, gt=0, le=100)
    quantity_grams_override: Optional[float] = Field(default=None, gt=0)
    meal_type: Optional[MealType] = None
    log_date: Optional[date] = None


class NutritionLogItemResponse(BaseModel):
    """A logged food item with its nutrition snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nutrition_log_id: str
    food_id: str
    serving_option_id: Optional[str]
    quantity_servings: float
    quantity_grams: float
    food_name_snapshot: str

    # Nutrition at time of logging
    calories_snapshot: float
    protein_snapshot: float
    carbs_snapshot: float
    fat_snapshot: float
    fiber_snapshot: float

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Meal Summary (all items for one meal)
# ---------------------------------------------------------------------------


class MealSummaryResponse(BaseModel):
    """Summary of a single meal (e.g. Lunch) for a given day."""

    meal_type: str
    items: list[NutritionLogItemResponse]
    subtotal: NutritionFacts


# ---------------------------------------------------------------------------
# Daily Nutrition Summary
# ---------------------------------------------------------------------------


class DailyNutritionResponse(BaseModel):
    """Full daily nutrition summary across all meals.

    Phase 5: informational only — no daily targets or deficit calculations.
    """

    log_date: date
    meals: list[MealSummaryResponse]
    total: NutritionFacts
    foods_logged_count: int
    is_empty: bool


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class NutritionHistoryEntry(BaseModel):
    """Lightweight per-day entry for historical view."""

    log_date: date
    total: NutritionFacts
    foods_logged_count: int


class NutritionHistoryResponse(BaseModel):
    entries: list[NutritionHistoryEntry]
    start_date: date
    end_date: date
