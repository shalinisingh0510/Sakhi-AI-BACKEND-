"""Nutrition Service — orchestration layer for food tracking (Phase 5).

Responsibilities:
  * Authorization via JWT → HealthPrivacyGate → HealthFeaturePolicy.can_use_nutrition_tracking()
  * Food search, food detail, category listing
  * Food log CRUD (create, update, delete log items)
  * Daily nutrition summary aggregation
  * Historical nutrition retrieval
  * Database seeding (on first run)
  * Allergen warning computation (backend-side, never in React)
  * Diet compatibility checks (backend-side)

Constraints (Phase 5):
  * No AI, no calorie goals, no deficit calculation
  * No wearable integration
  * No calorie targets or daily budgets
  * Nutrition values are informational only
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.domain.health.age_policy import AgePolicy
from app.domain.health.feature_policy import HealthFeaturePolicy
from app.domain.health.privacy import HealthPrivacyGate
from app.models.health_profile import HealthProfile
from app.models.nutrition import (
    DietType,
    Food,
    FoodServingOption,
    MealType,
    NutritionLog,
    NutritionLogItem,
)
from app.repositories.health import HealthProfileRepository
from app.repositories.nutrition import (
    FoodRepository,
    FoodServingOptionRepository,
    NutritionLogItemRepository,
    NutritionLogRepository,
)
from app.schemas.nutrition import (
    DailyNutritionResponse,
    FoodResponse,
    FoodSearchResponse,
    FoodSearchResultResponse,
    FoodServingOptionResponse,
    MealSummaryResponse,
    NutritionFacts,
    NutritionHistoryEntry,
    NutritionHistoryResponse,
    NutritionLogItemCreate,
    NutritionLogItemResponse,
    NutritionLogItemUpdate,
)
from app.services.nutrition_engine import NutritionEngine, NutritionFacts as EngineFacts

logger = logging.getLogger("sakhi.nutrition")


class NutritionService:
    """Orchestrates all nutrition tracking operations.

    Inject a SQLAlchemy Session per request. No business logic should
    bypass this service and query the DB directly.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._health_repo = HealthProfileRepository(session)
        self._food_repo = FoodRepository(session)
        self._serving_repo = FoodServingOptionRepository(session)
        self._log_repo = NutritionLogRepository(session)
        self._item_repo = NutritionLogItemRepository(session)
        self._engine = NutritionEngine()

    # -------------------------------------------------------------------------
    # Authorization
    # -------------------------------------------------------------------------

    def _assert_nutrition_access(self, user_id: str) -> HealthProfile:
        """Enforce the full Phase 1 security chain for nutrition access.

        Chain: JWT (caller) → HealthProfile existence → HealthPrivacyGate →
               AgePolicy → HealthFeaturePolicy.can_use_nutrition_tracking()
        """
        profile = self._health_repo.get_by_user_id(user_id)
        if not profile:
            raise HTTPException(404, "Health profile not found. Please complete your health profile first.")

        gate = HealthPrivacyGate.from_profile(
            authenticated_user_id=user_id,
            profile=profile,
        )
        gate.assert_owner(profile.user_id)

        age_policy = AgePolicy.from_dob(profile.date_of_birth)
        if not age_policy.is_health_hub_allowed():
            raise HTTPException(403, "Health Hub requires users to be 14 or older.")

        feature_policy = HealthFeaturePolicy.build(age_policy=age_policy, profile=profile)
        if not feature_policy.can_use_nutrition_tracking():
            raise HTTPException(
                403,
                "Nutrition tracking is not enabled. Please enable it in your health profile settings.",
            )

        return profile

    # -------------------------------------------------------------------------
    # Food Search & Discovery
    # -------------------------------------------------------------------------

    def search_foods(
        self,
        user_id: str,
        *,
        query: str = "",
        category: str | None = None,
        diet_type_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FoodSearchResponse:
        """Search the food database with optional filters.

        Backend computes allergen_warnings and is_diet_compatible
        from the user's health profile — never in the frontend.
        """
        profile = self._assert_nutrition_access(user_id)
        user_allergies = profile.food_allergies
        user_diet_type = profile.diet_type

        offset = (page - 1) * page_size
        foods, total = self._food_repo.search(
            query,
            diet_type_filter=diet_type_filter,
            category_filter=category,
            limit=page_size,
            offset=offset,
        )

        results = []
        for food in foods:
            serving = self._serving_repo.get_default_for_food(food.id)
            allergen_warnings = NutritionEngine.check_allergen_conflicts(food, user_allergies)
            is_compatible = NutritionEngine.is_diet_compatible(food, user_diet_type)

            results.append(
                FoodSearchResultResponse(
                    id=food.id,
                    name_en=food.name_en,
                    name_hi=food.name_hi,
                    category=food.category,
                    diet_type=food.diet_type,
                    calories_per_100g=food.calories_per_100g,
                    data_quality=food.data_quality,
                    default_serving_label=serving.serving_label if serving else None,
                    default_serving_grams=serving.quantity_grams if serving else None,
                    allergen_warnings=allergen_warnings,
                    is_diet_compatible=is_compatible,
                )
            )

        return FoodSearchResponse(
            results=results,
            total_count=total,
            page=page,
            page_size=page_size,
            query=query or None,
        )

    def get_food_detail(self, user_id: str, food_id: str) -> FoodResponse:
        """Return full food detail with serving options and user-specific flags."""
        profile = self._assert_nutrition_access(user_id)

        food = self._food_repo.get_active_by_id(food_id)
        if not food:
            raise HTTPException(404, "Food not found.")

        servings = self._serving_repo.list_by_food(food.id)
        allergen_warnings = NutritionEngine.check_allergen_conflicts(food, profile.food_allergies)
        is_compatible = NutritionEngine.is_diet_compatible(food, profile.diet_type)

        return FoodResponse(
            id=food.id,
            name_en=food.name_en,
            name_hi=food.name_hi,
            name_regional=food.name_regional,
            category=food.category,
            cuisine=food.cuisine,
            diet_type=food.diet_type,
            search_aliases=food.search_aliases,
            calories_per_100g=food.calories_per_100g,
            protein_g=food.protein_g,
            carbs_g=food.carbs_g,
            fat_g=food.fat_g,
            fiber_g=food.fiber_g,
            sugar_g=food.sugar_g,
            sodium_mg=food.sodium_mg,
            iron_mg=food.iron_mg,
            calcium_mg=food.calcium_mg,
            folate_mcg=food.folate_mcg,
            data_quality=food.data_quality,
            data_source=food.data_source,
            is_active=food.is_active,
            serving_options=[
                FoodServingOptionResponse(
                    id=s.id,
                    food_id=s.food_id,
                    serving_label=s.serving_label,
                    quantity_grams=s.quantity_grams,
                    is_default=s.is_default,
                    sort_order=s.sort_order,
                )
                for s in servings
            ],
            allergen_warnings=allergen_warnings,
            is_diet_compatible=is_compatible,
        )

    # -------------------------------------------------------------------------
    # Food Logging
    # -------------------------------------------------------------------------

    def log_food(self, user_id: str, data: NutritionLogItemCreate) -> NutritionLogItemResponse:
        """Add a food item to a meal log for the given date.

        Auto-creates NutritionLog if one doesn't exist for (profile, date, meal).
        Computes and stores nutrition snapshot at log time.
        """
        profile = self._assert_nutrition_access(user_id)

        food = self._food_repo.get_active_by_id(data.food_id)
        if not food:
            raise HTTPException(404, "Food not found.")

        # Resolve serving option
        serving_option: FoodServingOption | None = None
        if data.serving_option_id:
            serving_option = self._serving_repo.get_by_id_and_food(data.serving_option_id, food.id)
            if not serving_option:
                raise HTTPException(404, "Serving option not found for this food.")

        # Calculate quantity in grams
        quantity_grams = NutritionEngine.resolve_quantity_grams(
            serving_option, data.quantity_servings, data.quantity_grams_override
        )

        # Calculate nutrition snapshot
        nutrition = NutritionEngine.calculate_nutrition(food, quantity_grams)

        with transactional(self._session) as session:
            # Get or create NutritionLog for this meal
            nutrition_log = self._log_repo.get_by_profile_date_meal(
                profile.id, data.log_date, data.meal_type.value
            )
            if not nutrition_log:
                nutrition_log = NutritionLog(
                    id=uuid4().hex,
                    health_profile_id=profile.id,
                    log_date=data.log_date,
                    meal_type=data.meal_type.value,
                )
                session.add(nutrition_log)
                session.flush()

            # Create log item with nutrition snapshot
            item = NutritionLogItem(
                id=uuid4().hex,
                nutrition_log_id=nutrition_log.id,
                food_id=food.id,
                serving_option_id=serving_option.id if serving_option else None,
                quantity_servings=data.quantity_servings,
                quantity_grams=quantity_grams,
                calories_snapshot=nutrition.calories,
                protein_snapshot=nutrition.protein_g,
                carbs_snapshot=nutrition.carbs_g,
                fat_snapshot=nutrition.fat_g,
                fiber_snapshot=nutrition.fiber_g,
                food_name_snapshot=food.name_en,
            )
            session.add(item)

        logger.info("Nutrition log item created: user=%s", user_id)
        return self._item_to_response(item)

    def update_log_item(
        self, user_id: str, item_id: str, data: NutritionLogItemUpdate
    ) -> NutritionLogItemResponse:
        """Update a food log item (quantity, serving, meal, date).

        Re-calculates and overwrites the nutrition snapshot on update.
        """
        profile = self._assert_nutrition_access(user_id)
        item = self._find_item_for_user(item_id, profile.id)

        food = self._food_repo.get_active_by_id(item.food_id)
        if not food:
            raise HTTPException(404, "Referenced food is no longer available.")

        with transactional(self._session) as session:
            # Update meal / date if requested (may need to move to different log)
            new_meal = data.meal_type.value if data.meal_type else item.nutrition_log_id
            new_date = data.log_date

            if data.meal_type or data.log_date:
                old_log = self._log_repo.get_by_id(item.nutrition_log_id)
                target_meal = data.meal_type.value if data.meal_type else old_log.meal_type
                target_date = data.log_date if data.log_date else old_log.log_date

                target_log = self._log_repo.get_by_profile_date_meal(
                    profile.id, target_date, target_meal
                )
                if not target_log:
                    target_log = NutritionLog(
                        id=uuid4().hex,
                        health_profile_id=profile.id,
                        log_date=target_date,
                        meal_type=target_meal,
                    )
                    session.add(target_log)
                    session.flush()
                item.nutrition_log_id = target_log.id

            # Update serving and quantity
            serving_option: FoodServingOption | None = None
            if data.serving_option_id:
                serving_option = self._serving_repo.get_by_id_and_food(
                    data.serving_option_id, food.id
                )
                if not serving_option:
                    raise HTTPException(404, "Serving option not found for this food.")
                item.serving_option_id = serving_option.id
            elif item.serving_option_id:
                serving_option = self._serving_repo.get_by_id(item.serving_option_id)

            quantity_servings = data.quantity_servings if data.quantity_servings else item.quantity_servings
            quantity_grams_override = data.quantity_grams_override
            item.quantity_servings = quantity_servings

            # Re-resolve grams and re-calculate snapshot
            quantity_grams = NutritionEngine.resolve_quantity_grams(
                serving_option, quantity_servings, quantity_grams_override
            )
            item.quantity_grams = quantity_grams

            nutrition = NutritionEngine.calculate_nutrition(food, quantity_grams)
            item.calories_snapshot = nutrition.calories
            item.protein_snapshot = nutrition.protein_g
            item.carbs_snapshot = nutrition.carbs_g
            item.fat_snapshot = nutrition.fat_g
            item.fiber_snapshot = nutrition.fiber_g

            session.add(item)

        logger.info("Nutrition log item updated: user=%s item=%s", user_id, item_id)
        return self._item_to_response(item)

    def delete_log_item(self, user_id: str, item_id: str) -> None:
        """Delete a food log item."""
        profile = self._assert_nutrition_access(user_id)
        item = self._find_item_for_user(item_id, profile.id)

        with transactional(self._session) as session:
            session.delete(item)

        logger.info("Nutrition log item deleted: user=%s item=%s", user_id, item_id)

    # -------------------------------------------------------------------------
    # Daily Summary & History
    # -------------------------------------------------------------------------

    def get_today_summary(self, user_id: str, log_date: date) -> DailyNutritionResponse:
        """Return the daily nutrition summary for a given date."""
        profile = self._assert_nutrition_access(user_id)
        return self._build_daily_summary(profile.id, log_date)

    def get_history(
        self,
        user_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> NutritionHistoryResponse:
        """Return per-day nutrition totals for a date range.

        Defaults to last 7 days if no dates provided.
        """
        profile = self._assert_nutrition_access(user_id)

        today = date.today()
        end = end_date or today
        start = start_date or (today - timedelta(days=6))

        logs = self._log_repo.list_by_profile_date_range(profile.id, start, end)
        log_ids = [log.id for log in logs]
        all_items = self._item_repo.list_by_log_ids(log_ids)

        # Group items by log_id, then by log_date
        log_date_map: dict[str, date] = {log.id: log.log_date for log in logs}
        items_by_date: dict[date, list[NutritionLogItem]] = defaultdict(list)
        for item in all_items:
            log_d = log_date_map.get(item.nutrition_log_id)
            if log_d:
                items_by_date[log_d].append(item)

        entries = []
        for log_d, day_items in sorted(items_by_date.items(), reverse=True):
            total = NutritionEngine.aggregate_items(day_items)
            entries.append(
                NutritionHistoryEntry(
                    log_date=log_d,
                    total=NutritionFacts(
                        calories=total.calories,
                        protein_g=total.protein_g,
                        carbs_g=total.carbs_g,
                        fat_g=total.fat_g,
                        fiber_g=total.fiber_g,
                    ),
                    foods_logged_count=len(day_items),
                )
            )

        return NutritionHistoryResponse(
            entries=entries,
            start_date=start,
            end_date=end,
        )

    # -------------------------------------------------------------------------
    # Database Seeding
    # -------------------------------------------------------------------------

    def seed_food_database(self, user_id: str) -> dict[str, int]:
        """Seed the food database from nutrition_seed.py.

        Only runs if the foods table is empty.
        Should be called by an admin or management command, not by regular users.

        Returns a dict with counts: {"foods_added": N, "servings_added": M}
        """
        # Note: no user-facing nutrition access check here — this is an admin op.
        # The calling endpoint should verify admin role.
        existing_count = self._session.query(Food).count()
        if existing_count > 0:
            logger.info("Food database already seeded (%d foods). Skipping.", existing_count)
            return {"foods_added": 0, "servings_added": 0, "skipped": True}

        from app.db.nutrition_seed import SEED_FOODS

        foods_added = 0
        servings_added = 0

        with transactional(self._session) as session:
            for seed in SEED_FOODS:
                food_id = uuid4().hex
                food = Food(
                    id=food_id,
                    name_en=seed.name_en,
                    name_hi=seed.name_hi,
                    name_regional=seed.name_regional,
                    category=seed.category,
                    cuisine=seed.cuisine,
                    diet_type=seed.diet_type,
                    calories_per_100g=seed.calories_per_100g,
                    protein_g=seed.protein_g,
                    carbs_g=seed.carbs_g,
                    fat_g=seed.fat_g,
                    fiber_g=seed.fiber_g,
                    sugar_g=seed.sugar_g,
                    sodium_mg=seed.sodium_mg,
                    iron_mg=seed.iron_mg,
                    calcium_mg=seed.calcium_mg,
                    folate_mcg=seed.folate_mcg,
                    data_quality=seed.data_quality,
                    data_source=seed.data_source,
                    is_active=True,
                )
                food.search_aliases = seed.search_aliases
                session.add(food)
                foods_added += 1

                for i, svo in enumerate(seed.serving_options):
                    serving = FoodServingOption(
                        id=uuid4().hex,
                        food_id=food_id,
                        serving_label=svo.serving_label,
                        quantity_grams=svo.quantity_grams,
                        is_default=svo.is_default,
                        sort_order=i,
                    )
                    session.add(serving)
                    servings_added += 1

        logger.info("Food database seeded: %d foods, %d servings", foods_added, servings_added)
        return {"foods_added": foods_added, "servings_added": servings_added}

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _build_daily_summary(self, health_profile_id: str, log_date: date) -> DailyNutritionResponse:
        """Build a DailyNutritionResponse for a profile and date."""
        logs = self._log_repo.list_by_profile_and_date(health_profile_id, log_date)
        if not logs:
            return DailyNutritionResponse(
                log_date=log_date,
                meals=[],
                total=NutritionFacts(),
                foods_logged_count=0,
                is_empty=True,
            )

        log_ids = [log.id for log in logs]
        all_items = self._item_repo.list_by_log_ids(log_ids)
        items_by_log: dict[str, list[NutritionLogItem]] = defaultdict(list)
        for item in all_items:
            items_by_log[item.nutrition_log_id].append(item)

        meal_order = [MealType.BREAKFAST, MealType.LUNCH, MealType.SNACK, MealType.DINNER, MealType.OTHER]
        log_by_meal = {log.meal_type: log for log in logs}

        meals = []
        grand_total = EngineFacts.zero()
        total_foods = 0

        for meal_enum in meal_order:
            meal_key = meal_enum.value
            log = log_by_meal.get(meal_key)
            if not log:
                continue

            items = items_by_log.get(log.id, [])
            subtotal = NutritionEngine.aggregate_items(items)
            grand_total = grand_total + subtotal
            total_foods += len(items)

            meals.append(
                MealSummaryResponse(
                    meal_type=meal_key,
                    items=[self._item_to_response(i) for i in items],
                    subtotal=NutritionFacts(
                        calories=subtotal.calories,
                        protein_g=subtotal.protein_g,
                        carbs_g=subtotal.carbs_g,
                        fat_g=subtotal.fat_g,
                        fiber_g=subtotal.fiber_g,
                    ),
                )
            )

        return DailyNutritionResponse(
            log_date=log_date,
            meals=meals,
            total=NutritionFacts(
                calories=grand_total.calories,
                protein_g=grand_total.protein_g,
                carbs_g=grand_total.carbs_g,
                fat_g=grand_total.fat_g,
                fiber_g=grand_total.fiber_g,
            ),
            foods_logged_count=total_foods,
            is_empty=(total_foods == 0),
        )

    def _find_item_for_user(self, item_id: str, health_profile_id: str) -> NutritionLogItem:
        """Find a NutritionLogItem that belongs to the user's profile.

        Security: verifies ownership via nutrition_log → health_profile_id chain.
        Raises 404 if not found or not owned by the user.
        """
        item = self._item_repo.get_by_id(item_id)
        if not item:
            raise HTTPException(404, "Food log item not found.")

        log = self._log_repo.get_by_id(item.nutrition_log_id)
        if not log or log.health_profile_id != health_profile_id:
            raise HTTPException(404, "Food log item not found.")

        return item

    def _item_to_response(self, item: NutritionLogItem) -> NutritionLogItemResponse:
        return NutritionLogItemResponse(
            id=item.id,
            nutrition_log_id=item.nutrition_log_id,
            food_id=item.food_id,
            serving_option_id=item.serving_option_id,
            quantity_servings=item.quantity_servings,
            quantity_grams=item.quantity_grams,
            food_name_snapshot=item.food_name_snapshot,
            calories_snapshot=item.calories_snapshot,
            protein_snapshot=item.protein_snapshot,
            carbs_snapshot=item.carbs_snapshot,
            fat_snapshot=item.fat_snapshot,
            fiber_snapshot=item.fiber_snapshot,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
