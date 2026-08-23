"""Health domain constants — enums, event types, and sources.

These constants form the vocabulary shared across the health domain.
They must NOT leak provider-specific terminology into the rest of the
application.
"""

from __future__ import annotations

from enum import StrEnum


# ---------------------------------------------------------------------------
# Wellness disclaimer — must be surfaced in UI and AI responses.
# ---------------------------------------------------------------------------

WELLNESS_DISCLAIMER = (
    "Sakhi AI provides wellness tracking and health education only. "
    "It does not diagnose medical conditions, predict medical emergencies, "
    "or replace professional medical advice. Always consult a qualified "
    "healthcare provider for medical concerns."
)


# ---------------------------------------------------------------------------
# Event sources — where health data originates.
# ---------------------------------------------------------------------------

class EventSource(StrEnum):
    """Origin of a health event."""

    MANUAL = "manual"
    HEALTH_CONNECT = "health_connect"
    HEALTHKIT = "healthkit"
    SAMSUNG_HEALTH = "samsung_health"
    WEARABLE = "wearable"


# ---------------------------------------------------------------------------
# Event types — what kind of health data it represents.
# ---------------------------------------------------------------------------

class EventType(StrEnum):
    """Canonical event types for the health domain."""

    STEPS = "steps"
    SLEEP = "sleep"
    EXERCISE = "exercise"
    WATER = "water"
    WEIGHT = "weight"
    HEART_RATE = "heart_rate"
    NUTRITION = "nutrition"
    CALORIES_BURNED = "calories_burned"
    CYCLE = "cycle"
    SYMPTOMS = "symptoms"
    MOOD = "mood"
    ENERGY = "energy"


# ---------------------------------------------------------------------------
# Age group boundaries used for policy decisions.
# ---------------------------------------------------------------------------

TEEN_AGE_MIN = 14
TEEN_AGE_MAX = 17
ADULT_AGE_MIN = 18
HEALTH_HUB_MIN_AGE = 14   # users below this age cannot access the Health Hub
