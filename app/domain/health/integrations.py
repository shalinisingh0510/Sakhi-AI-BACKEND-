"""Health data provider abstraction — wearable / platform integration.

All external health data sources (Health Connect, HealthKit, Samsung
Health, wearable SDKs) MUST implement this interface and map their
native events into the canonical ``HealthEventSchema``.

Phase 0: Abstract base class only — no concrete providers yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.health.events import HealthEventSchema


class HealthDataProvider(ABC):
    """Abstract interface for external health data sources.

    Concrete implementations (future phases):
    - ``HealthConnectProvider``  (Android Health Connect)
    - ``HealthKitProvider``      (Apple HealthKit)
    - ``SamsungHealthProvider``  (Samsung Health SDK)

    Each adapter is responsible for:
    1. Authenticating with the platform.
    2. Fetching raw events.
    3. Mapping raw events → ``HealthEventSchema``.
    4. Never leaking provider-specific schemas beyond this boundary.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'Health Connect')."""
        ...

    @property
    @abstractmethod
    def source_key(self) -> str:
        """Canonical source key from ``EventSource`` enum."""
        ...

    @abstractmethod
    async def is_available(self, user_id: str) -> bool:
        """Check whether this provider is configured for the user."""
        ...

    @abstractmethod
    async def fetch_events(
        self,
        user_id: str,
        *,
        event_types: list[str] | None = None,
        since: str | None = None,
    ) -> list[HealthEventSchema]:
        """Fetch and map events into canonical schema.

        Args:
            user_id: The authenticated Sakhi user ID.
            event_types: Optional filter by event type.
            since: Optional ISO-8601 timestamp to fetch events after.

        Returns:
            List of ``HealthEventSchema`` instances.
        """
        ...

    @abstractmethod
    async def revoke_access(self, user_id: str) -> None:
        """Disconnect the user's account from this provider."""
        ...
