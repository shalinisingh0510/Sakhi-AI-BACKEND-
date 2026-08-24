"""Deterministic Nutrition Calculation Engine (Phase 5).

IMPORTANT:
  * This engine performs ONLY deterministic math — no AI, no heuristics.
  * All calculations are based on the canonical 100g nutrition values stored
    in the Food model. Serving sizes convert user quantity to grams.
  * Snapshots are computed here and stored on NutritionLogItem at log time.

Usage::

    engine = NutritionEngine()
    grams = engine.resolve_quantity_grams(serving_option, quantity_servings, override)
    facts = engine.calculate_nutrition(food, grams)
    daily = engine.aggregate_daily(items)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.models.nutrition import Food, FoodServingOption, NutritionLogItem


@dataclass(frozen=True)
class NutritionFacts:
    """Immutable nutrition calculation result."""

    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0

    def __add__(self, other: "NutritionFacts") -> "NutritionFacts":
        return NutritionFacts(
            calories=round(self.calories + other.calories, 2),
            protein_g=round(self.protein_g + other.protein_g, 2),
            carbs_g=round(self.carbs_g + other.carbs_g, 2),
            fat_g=round(self.fat_g + other.fat_g, 2),
            fiber_g=round(self.fiber_g + other.fiber_g, 2),
        )

    @classmethod
    def zero(cls) -> "NutritionFacts":
        return cls()


class NutritionEngine:
    """Stateless deterministic nutrition calculation engine.

    All methods are pure functions that take data objects and return results.
    No DB access, no AI calls, no side effects.
    """

    # Default serving when no serving option is found: 100g
    DEFAULT_SERVING_GRAMS = 100.0

    @staticmethod
    def resolve_quantity_grams(
        serving_option: FoodServingOption | None,
        quantity_servings: float,
        quantity_grams_override: float | None,
    ) -> float:
        """Resolve the canonical gram quantity for a food log item.

        Priority:
          1. quantity_grams_override — user explicitly picked "100g" or typed a number
          2. serving_option.quantity_grams × quantity_servings — standard serving
          3. DEFAULT_SERVING_GRAMS × quantity_servings — fallback (shouldn't occur)

        Returns grams rounded to 2 decimal places.
        """
        if quantity_grams_override is not None and quantity_grams_override > 0:
            return round(quantity_grams_override, 2)

        if serving_option is not None:
            return round(serving_option.quantity_grams * quantity_servings, 2)

        # Fallback: treat quantity_servings as direct grams (shouldn't normally happen)
        return round(NutritionEngine.DEFAULT_SERVING_GRAMS * quantity_servings, 2)

    @staticmethod
    def calculate_nutrition(food: Food, quantity_grams: float) -> NutritionFacts:
        """Calculate nutrition for a given food at a given gram quantity.

        Formula: (value_per_100g / 100) × quantity_grams
        Results rounded to 2 decimal places.
        """
        if quantity_grams <= 0:
            return NutritionFacts.zero()

        multiplier = quantity_grams / 100.0

        return NutritionFacts(
            calories=round(food.calories_per_100g * multiplier, 2),
            protein_g=round(food.protein_g * multiplier, 2),
            carbs_g=round(food.carbs_g * multiplier, 2),
            fat_g=round(food.fat_g * multiplier, 2),
            fiber_g=round(food.fiber_g * multiplier, 2),
        )

    @staticmethod
    def aggregate_items(items: Sequence[NutritionLogItem]) -> NutritionFacts:
        """Sum nutrition snapshots across a list of log items.

        IMPORTANT: Uses stored snapshot values — NOT re-calculated from food.
        This preserves historical accuracy even if food data changes.
        """
        totals = NutritionFacts.zero()
        for item in items:
            totals = totals + NutritionFacts(
                calories=item.calories_snapshot,
                protein_g=item.protein_snapshot,
                carbs_g=item.carbs_snapshot,
                fat_g=item.fat_snapshot,
                fiber_g=item.fiber_snapshot,
            )
        return totals

    @staticmethod
    def check_allergen_conflicts(
        food: Food,
        user_allergies: list[str],
    ) -> list[str]:
        """Identify allergens from user profile that may be present in the food.

        Checks food.search_aliases (which include ingredient names) against
        user allergies. Returns a list of matched allergen strings.

        This is a conservative check: any partial keyword match is flagged.
        Never silently ignores a potential allergen conflict.
        """
        if not user_allergies:
            return []

        food_terms = food.all_search_terms()
        warnings = []

        for allergen in user_allergies:
            allergen_lower = allergen.strip().lower()
            if not allergen_lower:
                continue
            for term in food_terms:
                if allergen_lower in term:
                    warnings.append(allergen)
                    break

        return warnings

    @staticmethod
    def is_diet_compatible(food: Food, user_diet_type: str) -> bool:
        """Check if a food is compatible with the user's dietary preference.

        Hierarchy (most restrictive first):
          VEGAN ⊂ VEGETARIAN ⊂ EGGETARIAN ⊂ NON_VEGETARIAN

        A vegan user cannot eat vegetarian (dairy) foods.
        A vegetarian user cannot eat non-vegetarian foods.
        An eggetarian user can eat eggs but not meat/seafood.
        A non-vegetarian user can eat everything.
        """
        user = user_diet_type.upper()
        food_diet = food.diet_type.upper()

        if user == "NON_VEGETARIAN":
            return True  # Eats everything
        if user == "EGGETARIAN":
            return food_diet in ("VEGETARIAN", "VEGAN", "EGGETARIAN")
        if user == "VEGETARIAN":
            return food_diet in ("VEGETARIAN", "VEGAN")
        if user == "VEGAN":
            return food_diet == "VEGAN"

        # Unknown diet type — default to compatible (safe degradation)
        return True
