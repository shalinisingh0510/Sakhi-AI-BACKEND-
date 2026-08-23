"""Health domain — bounded context for women's health & wellness.

This package establishes the architectural boundary between:
- Infrastructure health checks (``GET /api/v1/health``)
- User health & wellness tracking (future ``/api/v1/health-profile``, etc.)

Sub-modules:
- ``age_policy``: Server-side age-based feature gating
- ``constants``: Enums, event types, sources
- ``events``: Canonical ``HealthEvent`` schema
- ``integrations``: Abstract wearable/health data provider
- ``privacy``: Health data access control boundary
"""

from app.domain.health.age_policy import AgePolicy
from app.domain.health.constants import EventSource, EventType, WELLNESS_DISCLAIMER
from app.domain.health.events import HealthEventSchema
from app.domain.health.feature_policy import HealthFeaturePolicy
from app.domain.health.integrations import HealthDataProvider
from app.domain.health.privacy import HealthPrivacyGate

__all__ = [
    "AgePolicy",
    "EventSource",
    "EventType",
    "HealthDataProvider",
    "HealthEventSchema",
    "HealthFeaturePolicy",
    "HealthPrivacyGate",
    "WELLNESS_DISCLAIMER",
]
