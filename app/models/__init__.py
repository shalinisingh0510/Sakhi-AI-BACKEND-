"""SQLAlchemy ORM models for Sakhi AI.

Import all model modules here so that ``Base.metadata`` discovers every
table when Alembic runs ``target_metadata = Base.metadata``.

**Important**: Existing tables (users, conversations, etc.) are still
managed by the ``psycopg``-based store classes.  Only *new* domain
models (health, wellness, etc.) should be added here.
"""

from app.db.base import Base  # noqa: F401 — re-export for Alembic
from app.models.activity import ActivityLog
from app.models.energy_log import EnergyLog
from app.models.health_profile import HealthCondition, HealthProfile
from app.models.menstrual_cycle import CycleLog, MenstrualCycle
from app.models.mood_log import MoodLog
from app.models.nutrition import Food, FoodServingOption, NutritionLog, NutritionLogItem
from app.models.symptom_log import SymptomLog

# This ensures Alembic can discover all models when it imports Base
__all__ = [
    "ActivityLog",
    "CycleLog",
    "EnergyLog",
    "Food",
    "FoodServingOption",
    "HealthCondition",
    "HealthProfile",
    "MenstrualCycle",
    "MoodLog",
    "NutritionLog",
    "NutritionLogItem",
    "SymptomLog",
]
