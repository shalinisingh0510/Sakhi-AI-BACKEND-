"""Repository classes for the Nutrition domain (Phase 5).

Follows the existing BaseRepository[ModelT] pattern from Phase 0.
All SQL logic lives here — services never query the DB directly.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.nutrition import Food, FoodServingOption, NutritionLog, NutritionLogItem
from app.repositories.base import BaseRepository


class FoodRepository(BaseRepository[Food]):
    """Repository for the foods table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Food)

    def search(
        self,
        query: str,
        *,
        diet_type_filter: str | None = None,
        category_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Food], int]:
        """Case-insensitive search across name_en, name_hi, name_regional, aliases.

        Returns (results, total_count) for pagination.
        """
        q = self._session.query(Food).filter(Food.is_active.is_(True))

        if query:
            pattern = f"%{query.lower()}%"
            q = q.filter(
                or_(
                    Food.name_en.ilike(pattern),
                    Food.name_hi.ilike(pattern),
                    Food.name_regional.ilike(pattern),
                    Food.search_aliases_json.ilike(pattern),
                )
            )

        if diet_type_filter:
            q = q.filter(Food.diet_type == diet_type_filter)

        if category_filter:
            q = q.filter(Food.category == category_filter)

        total = q.count()
        results = q.order_by(Food.name_en.asc()).offset(offset).limit(limit).all()
        return list(results), total

    def get_active_by_id(self, food_id: str) -> Food | None:
        """Return an active food by ID, or None."""
        return (
            self._session.query(Food)
            .filter(Food.id == food_id, Food.is_active.is_(True))
            .first()
        )

    def list_by_category(
        self, category: str, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Food], int]:
        """List active foods in a category with pagination."""
        q = (
            self._session.query(Food)
            .filter(Food.category == category, Food.is_active.is_(True))
        )
        total = q.count()
        results = q.order_by(Food.name_en.asc()).offset(offset).limit(limit).all()
        return list(results), total

    def list_all_active(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Food], int]:
        """List all active foods paginated."""
        q = self._session.query(Food).filter(Food.is_active.is_(True))
        total = q.count()
        results = q.order_by(Food.name_en.asc()).offset(offset).limit(limit).all()
        return list(results), total


class FoodServingOptionRepository(BaseRepository[FoodServingOption]):
    """Repository for food_serving_options table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, FoodServingOption)

    def list_by_food(self, food_id: str) -> list[FoodServingOption]:
        """Return all serving options for a food, ordered by sort_order."""
        return (
            self._session.query(FoodServingOption)
            .filter(FoodServingOption.food_id == food_id)
            .order_by(FoodServingOption.sort_order.asc())
            .all()
        )

    def get_default_for_food(self, food_id: str) -> FoodServingOption | None:
        """Return the default serving option for a food."""
        return (
            self._session.query(FoodServingOption)
            .filter(
                FoodServingOption.food_id == food_id,
                FoodServingOption.is_default.is_(True),
            )
            .first()
        )

    def get_by_id_and_food(
        self, serving_id: str, food_id: str
    ) -> FoodServingOption | None:
        """Return a serving option only if it belongs to the given food."""
        return (
            self._session.query(FoodServingOption)
            .filter(
                FoodServingOption.id == serving_id,
                FoodServingOption.food_id == food_id,
            )
            .first()
        )


class NutritionLogRepository(BaseRepository[NutritionLog]):
    """Repository for nutrition_logs table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NutritionLog)

    def get_by_profile_date_meal(
        self, health_profile_id: str, log_date: date, meal_type: str
    ) -> NutritionLog | None:
        """Return existing log for profile + date + meal, or None."""
        return (
            self._session.query(NutritionLog)
            .filter(
                NutritionLog.health_profile_id == health_profile_id,
                NutritionLog.log_date == log_date,
                NutritionLog.meal_type == meal_type,
            )
            .first()
        )

    def list_by_profile_and_date(
        self, health_profile_id: str, log_date: date
    ) -> list[NutritionLog]:
        """Return all meal logs for a profile on a given date."""
        return (
            self._session.query(NutritionLog)
            .filter(
                NutritionLog.health_profile_id == health_profile_id,
                NutritionLog.log_date == log_date,
            )
            .order_by(NutritionLog.meal_type.asc())
            .all()
        )

    def list_by_profile_date_range(
        self,
        health_profile_id: str,
        start_date: date,
        end_date: date,
    ) -> list[NutritionLog]:
        """Return all logs for a date range, for history view."""
        return (
            self._session.query(NutritionLog)
            .filter(
                NutritionLog.health_profile_id == health_profile_id,
                NutritionLog.log_date >= start_date,
                NutritionLog.log_date <= end_date,
            )
            .order_by(NutritionLog.log_date.desc(), NutritionLog.meal_type.asc())
            .all()
        )


class NutritionLogItemRepository(BaseRepository[NutritionLogItem]):
    """Repository for nutrition_log_items table."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NutritionLogItem)

    def list_by_log(self, nutrition_log_id: str) -> list[NutritionLogItem]:
        """Return all items in a nutrition log, ordered by creation time."""
        return (
            self._session.query(NutritionLogItem)
            .filter(NutritionLogItem.nutrition_log_id == nutrition_log_id)
            .order_by(NutritionLogItem.created_at.asc())
            .all()
        )

    def get_by_id_and_log(
        self, item_id: str, nutrition_log_id: str
    ) -> NutritionLogItem | None:
        """Return an item only if it belongs to the given log."""
        return (
            self._session.query(NutritionLogItem)
            .filter(
                NutritionLogItem.id == item_id,
                NutritionLogItem.nutrition_log_id == nutrition_log_id,
            )
            .first()
        )

    def list_by_log_ids(self, log_ids: list[str]) -> list[NutritionLogItem]:
        """Return all items across multiple log IDs (used for daily summary)."""
        if not log_ids:
            return []
        return (
            self._session.query(NutritionLogItem)
            .filter(NutritionLogItem.nutrition_log_id.in_(log_ids))
            .order_by(
                NutritionLogItem.nutrition_log_id.asc(),
                NutritionLogItem.created_at.asc(),
            )
            .all()
        )
