"""Nutrition API endpoints (Phase 5).

All endpoints enforce the full security chain:
  JWT → get_current_user → NutritionService._assert_nutrition_access()

Routes:
  GET  /nutrition/foods           — search / list foods
  GET  /nutrition/foods/{id}      — food detail
  POST /nutrition/logs            — log a food item
  GET  /nutrition/logs/today      — today's nutrition summary
  GET  /nutrition/logs/history    — date-range history
  PATCH /nutrition/logs/items/{id} — update log item
  DELETE /nutrition/logs/items/{id} — delete log item
  POST /nutrition/admin/seed      — seed food database (admin only)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.dependencies import get_db
from app.schemas.nutrition import (
    DailyNutritionResponse,
    FoodResponse,
    FoodSearchResponse,
    NutritionHistoryResponse,
    NutritionLogItemCreate,
    NutritionLogItemResponse,
    NutritionLogItemUpdate,
)
from app.services.auth import StoredUser
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


def get_nutrition_service(db: Session = Depends(get_db)) -> NutritionService:
    return NutritionService(db)


# ---------------------------------------------------------------------------
# Food Search & Discovery
# ---------------------------------------------------------------------------


@router.get("/foods", response_model=FoodSearchResponse)
def search_foods(
    q: str = Query(default="", description="Food name search query"),
    category: str | None = Query(default=None, description="Filter by food category"),
    diet_type: str | None = Query(default=None, description="Filter by diet type (VEGETARIAN, VEGAN, etc.)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=50, description="Items per page"),
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Search or browse the food database.

    - Searches name_en, name_hi, regional names, and aliases
    - Returns allergen_warnings computed from user's health profile
    - Returns is_diet_compatible flag based on user's diet preference
    """
    return nutrition_service.search_foods(
        current_user.id,
        query=q,
        category=category,
        diet_type_filter=diet_type,
        page=page,
        page_size=page_size,
    )


@router.get("/foods/{food_id}", response_model=FoodResponse)
def get_food_detail(
    food_id: str,
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Get full food detail including serving options, nutrition facts, and allergen warnings."""
    return nutrition_service.get_food_detail(current_user.id, food_id)


# ---------------------------------------------------------------------------
# Food Logging
# ---------------------------------------------------------------------------


@router.post("/logs", response_model=NutritionLogItemResponse, status_code=status.HTTP_201_CREATED)
def log_food(
    data: NutritionLogItemCreate,
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Log a food item to a meal.

    Auto-creates the meal log if it doesn't exist for the given date + meal type.
    Nutrition snapshot is calculated and stored at log time.
    """
    return nutrition_service.log_food(current_user.id, data)


@router.get("/logs/today", response_model=DailyNutritionResponse)
def get_today_summary(
    local_date: date = Query(default_factory=date.today, description="Local date (YYYY-MM-DD)"),
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Get today's full nutrition summary (all meals, all items, totals).

    Note: Totals are informational only — no daily targets or deficit calculations in Phase 5.
    """
    return nutrition_service.get_today_summary(current_user.id, local_date)


@router.get("/logs/history", response_model=NutritionHistoryResponse)
def get_history(
    start_date: date | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Get daily nutrition totals for a date range.

    Defaults to last 7 days if no dates provided.
    Returns lightweight per-day summaries for historical view.
    """
    return nutrition_service.get_history(
        current_user.id, start_date=start_date, end_date=end_date
    )


@router.patch("/logs/items/{item_id}", response_model=NutritionLogItemResponse)
def update_log_item(
    item_id: str,
    data: NutritionLogItemUpdate,
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Update a food log item (quantity, serving, meal type, or date).

    Nutrition snapshot is re-calculated and overwritten on update.
    """
    return nutrition_service.update_log_item(current_user.id, item_id, data)


@router.delete("/logs/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log_item(
    item_id: str,
    current_user: StoredUser = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> None:
    """Delete a food log item.

    The meal log container (NutritionLog) remains even if all items are deleted.
    """
    nutrition_service.delete_log_item(current_user.id, item_id)
    return None


# ---------------------------------------------------------------------------
# Admin: Seed food database
# ---------------------------------------------------------------------------


@router.post("/admin/seed", status_code=status.HTTP_200_OK)
def seed_food_database(
    current_user: StoredUser = Depends(require_roles("admin")),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Any:
    """Seed the food database from built-in seed data.

    Admin only. Only runs if the database is empty.
    Returns the count of foods and serving options added.
    """
    return nutrition_service.seed_food_database(current_user.id)
