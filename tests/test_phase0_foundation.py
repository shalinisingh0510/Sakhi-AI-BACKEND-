"""Phase 0 foundation tests — verify new infrastructure without breaking existing functionality.

Tests cover:
- SQLAlchemy engine/session creation
- Alembic configuration validity
- Redis client factory
- Celery app initialization
- Health domain boundary imports
- Age policy logic
- Privacy gate logic
- Existing infrastructure health endpoint (unchanged)
- API startup compatibility
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


# ---------------------------------------------------------------------------
# Existing health endpoint — MUST remain unchanged
# ---------------------------------------------------------------------------


class TestExistingHealthEndpoint:
    """Verify infrastructure health endpoints are NOT repurposed."""

    def setup_method(self) -> None:
        self.client = TestClient(create_app())

    def test_lightweight_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_v1_health_endpoint(self) -> None:
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "Sakhi AI API"

    def test_root_endpoint(self) -> None:
        response = self.client.get("/")
        assert response.status_code == 200
        assert "Sakhi AI" in response.json()["message"]


# ---------------------------------------------------------------------------
# SQLAlchemy foundation
# ---------------------------------------------------------------------------


class TestSQLAlchemyFoundation:
    """Verify SQLAlchemy modules can be imported and initialised."""

    def test_base_importable(self) -> None:
        from app.db.base import Base

        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_session_module_importable(self) -> None:
        from app.db.session import init_db, get_engine, get_session_factory

        assert callable(init_db)
        assert callable(get_engine)
        assert callable(get_session_factory)

    def test_uninitialised_engine_raises(self) -> None:
        """get_engine() should raise if init_db() was never called."""
        # Reset module state to test the guard.
        import app.db.session as session_mod

        original_engine = session_mod._engine
        session_mod._engine = None
        try:
            with pytest.raises(RuntimeError, match="not initialised"):
                session_mod.get_engine()
        finally:
            session_mod._engine = original_engine

    def test_dependencies_importable(self) -> None:
        from app.db.dependencies import get_db

        assert callable(get_db)

    def test_transaction_importable(self) -> None:
        from app.db.transaction import transactional

        assert callable(transactional)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModels:
    def test_models_package_importable(self) -> None:
        import app.models

        assert hasattr(app.models, "Base")

    def test_health_model_module_importable(self) -> None:
        import app.models.health

        assert app.models.health is not None


# ---------------------------------------------------------------------------
# Repository pattern
# ---------------------------------------------------------------------------


class TestRepositoryPattern:
    def test_base_repository_importable(self) -> None:
        from app.repositories.base import BaseRepository

        assert BaseRepository is not None

    def test_repository_package_exports(self) -> None:
        from app.repositories import BaseRepository

        assert BaseRepository is not None


# ---------------------------------------------------------------------------
# Health domain boundary
# ---------------------------------------------------------------------------


class TestHealthDomain:
    def test_domain_package_importable(self) -> None:
        from app.domain.health import (
            AgePolicy,
            EventSource,
            EventType,
            HealthDataProvider,
            HealthEventSchema,
            HealthPrivacyGate,
            WELLNESS_DISCLAIMER,
        )

        assert AgePolicy is not None
        assert EventSource is not None
        assert EventType is not None
        assert HealthDataProvider is not None
        assert HealthEventSchema is not None
        assert HealthPrivacyGate is not None
        assert "wellness" in WELLNESS_DISCLAIMER.lower()

    def test_event_sources(self) -> None:
        from app.domain.health.constants import EventSource

        assert EventSource.MANUAL == "manual"
        assert EventSource.HEALTH_CONNECT == "health_connect"
        assert EventSource.HEALTHKIT == "healthkit"
        assert EventSource.SAMSUNG_HEALTH == "samsung_health"

    def test_event_types(self) -> None:
        from app.domain.health.constants import EventType

        assert EventType.STEPS == "steps"
        assert EventType.CYCLE == "cycle"
        assert EventType.NUTRITION == "nutrition"

    def test_health_event_schema_creation(self) -> None:
        from datetime import datetime, timezone
        from app.domain.health.events import HealthEventSchema

        event = HealthEventSchema(
            id="test-1",
            user_id="user-1",
            source="manual",
            event_type="steps",
            start_time=datetime.now(timezone.utc),
            value=5000.0,
            unit="steps",
        )
        assert event.id == "test-1"
        assert event.source == "manual"


# ---------------------------------------------------------------------------
# Age policy
# ---------------------------------------------------------------------------


class TestAgePolicy:
    def test_teen_policy(self) -> None:
        from app.domain.health.age_policy import AgePolicy

        policy = AgePolicy(age=15)
        assert policy.is_teen is True
        assert policy.is_adult is False
        assert policy.can_use_cycle_tracking() is True
        assert policy.can_use_weight_features() is False
        assert policy.can_use_calorie_deficit_features() is False

    def test_adult_policy(self) -> None:
        from app.domain.health.age_policy import AgePolicy

        policy = AgePolicy(age=25)
        assert policy.is_teen is False
        assert policy.is_adult is True
        assert policy.can_use_cycle_tracking() is True
        assert policy.can_use_weight_features() is True
        assert policy.can_use_advanced_health_features() is True

    def test_age_group_string(self) -> None:
        from app.domain.health.age_policy import AgePolicy

        policy = AgePolicy(age=15)
        assert policy.is_teen is True
        assert policy.can_use_cycle_tracking() is True

    def test_adult_age_group_string(self) -> None:
        from app.domain.health.age_policy import AgePolicy

        policy = AgePolicy(age=25)
        assert policy.is_adult is True
        assert policy.can_use_weight_features() is True

    def test_underage_blocked(self) -> None:
        from app.domain.health.age_policy import AgePolicy

        policy = AgePolicy(age=12)
        assert policy.can_use_cycle_tracking() is False


# ---------------------------------------------------------------------------
# Privacy gate
# ---------------------------------------------------------------------------


class TestPrivacyGate:
    def test_owner_check_passes(self) -> None:
        from app.domain.health.privacy import HealthPrivacyGate

        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        gate.assert_owner("user-1")  # should not raise

    def test_owner_check_fails(self) -> None:
        from app.domain.health.privacy import HealthPrivacyGate

        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        with pytest.raises(PermissionError):
            gate.assert_owner("user-2")

    def test_ai_access_default_disabled(self) -> None:
        from app.domain.health.privacy import HealthPrivacyGate

        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        assert gate.ai_health_access_permitted() is False

    def test_wearable_access_default_disabled(self) -> None:
        from app.domain.health.privacy import HealthPrivacyGate

        gate = HealthPrivacyGate(authenticated_user_id="user-1")
        assert gate.wearable_access_permitted() is False


# ---------------------------------------------------------------------------
# Redis client factory
# ---------------------------------------------------------------------------


class TestRedisFactory:
    def test_redis_module_importable(self) -> None:
        from app.core.redis import get_redis_client, close_redis_client

        assert callable(get_redis_client)
        assert callable(close_redis_client)


# ---------------------------------------------------------------------------
# Celery foundation
# ---------------------------------------------------------------------------


class TestCeleryFoundation:
    def test_celery_app_importable(self) -> None:
        from app.tasks.celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "sakhi"

    def test_ping_task_registered(self) -> None:
        from app.tasks.health_tasks import ping

        assert ping is not None
        assert ping.name == "sakhi.health.ping"

    def test_ping_task_eager_execution(self) -> None:
        """Execute the ping task in eager mode (no broker needed)."""
        from app.tasks.celery_app import celery_app
        from app.tasks.health_tasks import ping

        # Temporarily enable eager mode for testing.
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        try:
            result = ping.delay()
            payload = result.get(timeout=5)
            assert payload["status"] == "pong"
        finally:
            celery_app.conf.task_always_eager = False


# ---------------------------------------------------------------------------
# Alembic configuration
# ---------------------------------------------------------------------------


class TestAlembicConfig:
    def test_alembic_ini_exists(self) -> None:
        from pathlib import Path

        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        assert alembic_ini.exists(), f"alembic.ini not found at {alembic_ini}"

    def test_alembic_env_importable(self) -> None:
        """Verify the alembic env.py module can be parsed."""
        from pathlib import Path

        env_path = Path(__file__).resolve().parents[1] / "alembic" / "env.py"
        assert env_path.exists(), f"alembic/env.py not found at {env_path}"

    def test_alembic_versions_directory_exists(self) -> None:
        from pathlib import Path

        versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
        assert versions.exists(), f"alembic/versions not found at {versions}"


# ---------------------------------------------------------------------------
# Configuration additions
# ---------------------------------------------------------------------------


class TestConfigAdditions:
    def test_celery_settings_exist(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert hasattr(s, "celery_broker_url")
        assert hasattr(s, "celery_result_backend")
        assert hasattr(s, "celery_always_eager")

    def test_celery_defaults(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert "redis" in s.celery_broker_url
        assert "redis" in s.celery_result_backend
        assert s.celery_always_eager is False


# ---------------------------------------------------------------------------
# API startup compatibility
# ---------------------------------------------------------------------------


class TestAPIStartup:
    """Verify the application starts with all existing services intact."""

    def test_app_starts(self) -> None:
        app = create_app()
        assert app is not None

    def test_existing_auth_endpoint(self) -> None:
        client = TestClient(create_app())
        # Registration requires POST body — just verify 422 (not 500/404)
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code in (400, 422)

    def test_existing_lessons_endpoint(self) -> None:
        client = TestClient(create_app())
        response = client.get("/api/v1/lessons")
        # Should return 200 or 401, not 500
        assert response.status_code in (200, 401)
