"""SQLAlchemy ORM models for Sakhi AI.

Import all model modules here so that ``Base.metadata`` discovers every
table when Alembic runs ``target_metadata = Base.metadata``.

**Important**: Existing tables (users, conversations, etc.) are still
managed by the ``psycopg``-based store classes.  Only *new* domain
models (health, wellness, etc.) should be added here.
"""

from app.db.base import Base  # noqa: F401 — re-export for Alembic

# Health domain models (Phase 1)
from app.models.health_profile import HealthCondition, HealthProfile  # noqa: F401

# Menstrual cycle models (Phase 2)
from app.models.menstrual_cycle import (  # noqa: F401
    CyclePrediction,
    MenstrualCycle,
    PeriodLog,
)

# Wellness models (Phase 3)
from app.models.symptom_log import SymptomLog  # noqa: F401
from app.models.mood_log import MoodLog  # noqa: F401
from app.models.energy_log import EnergyLog  # noqa: F401

# Nutrition models (Phase 5)
from app.models.nutrition import (  # noqa: F401
    Food,
    FoodServingOption,
    NutritionLog,
    NutritionLogItem,
)
