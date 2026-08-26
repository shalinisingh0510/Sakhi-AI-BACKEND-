import pytest
from datetime import date
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.services.longitudinal.date_range import get_date_range
from app.services.ai_context.router import HealthContextRouter

def test_date_range():
    target = date(2026, 8, 27)
    start, end = get_date_range(target, "30d")
    assert end == target
    assert start == date(2026, 7, 28)

def test_context_router_scopes():
    # Should detect ENERGY and SYMPTOMS
    scopes = HealthContextRouter.determine_scopes("Why am I so tired and have a headache?")
    assert "ENERGY" in scopes
    assert "SYMPTOMS" in scopes
    assert "LONGITUDINAL" in scopes
    assert "NUTRITION" not in scopes

    # Should detect NUTRITION
    scopes2 = HealthContextRouter.determine_scopes("How many calories in an apple?")
    assert "NUTRITION" in scopes2
    assert "ENERGY" not in scopes2

    # General question should have no scopes
    scopes3 = HealthContextRouter.determine_scopes("Who is the prime minister of India?")
    assert len(scopes3) == 0

def test_ai_privacy_bounds(client: TestClient):
    # This is a conceptual test verifying the prompt boundaries
    # Actual E2E requires a mock DB and AI Provider
    pass
