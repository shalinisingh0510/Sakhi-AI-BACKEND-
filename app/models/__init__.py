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
from app.models.rag import KnowledgeSource, KnowledgeDocument, DocumentChunk, TrustLevel, FreshnessStatus
from app.models.symptom_log import SymptomLog
from app.models.symptom_log import SymptomLog
from app.models.wellness_plan import WellnessGoal, WellnessPlan, PlanFrequency, PlanStatus
from app.models.integrations import HealthProviderConnection, ExternalSyncLog, ProviderType, ConnectionStatus, SyncStatus

# This ensures Alembic can discover all models when it imports Base
__all__ = [
    "ActivityLog",
    "CycleLog",
    "DocumentChunk",
    "EnergyLog",
    "Food",
    "FoodServingOption",
    "FreshnessStatus",
    "HealthCondition",
    "HealthProfile",
    "KnowledgeDocument",
    "KnowledgeSource",
    "MenstrualCycle",
    "MoodLog",
    "NutritionLog",
    "NutritionLogItem",
    "SymptomLog",
    "TrustLevel",
    "WellnessGoal",
    "WellnessPlan",
    "PlanFrequency",
    "PlanStatus",
    "HealthProviderConnection",
    "ExternalSyncLog",
    "ProviderType",
    "ConnectionStatus",
    "SyncStatus",
]
