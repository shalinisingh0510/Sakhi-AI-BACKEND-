from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.calculators import router as calculators_router
from app.services.calculators import CalculatorService
from app.schemas.calculators import (
    OvulationRequest,
    HcgRequest,
    TimeUnit,
    PregnancyTestRequest,
    PregnancyTestMethod,
    MenstrualCycleRequest,
    PeriodRequest,
    ImplantationRequest,
    ImplantationMethod,
    PregnancyWeeksToMonthsRequest,
    DueDateRequest,
    DueDateMethod,
    IvfDueDateRequest,
    IvfTransferType,
    UltrasoundDueDateRequest,
)

# Lightweight test app dedicated to calculators (no DB dependency required)
app = FastAPI()
app.include_router(calculators_router, prefix="/api/v1")
client = TestClient(app)


def test_calculator_catalog():
    response = client.get("/api/v1/calculators/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "calculators" in data
    assert len(data["calculators"]) == 10
    slugs = {c["slug"] for c in data["calculators"]}
    expected_slugs = {
        "ovulation-calculator",
        "hcg-calculator",
        "pregnancy-test-calculator",
        "menstrual-cycle-calculator",
        "period-calculator",
        "implantation-calculator",
        "pregnancy-weeks-to-months-calculator",
        "due-date-calculator",
        "ivf-due-date-calculator",
        "due-date-by-ultrasound",
    }
    assert slugs == expected_slugs


def test_ovulation_calculator():
    payload = {"last_period_date": "2026-10-01", "cycle_length": 28}
    response = client.post("/api/v1/calculators/ovulation", json=payload)
    assert response.status_code == 200
    data = response.json()
    # 28 days cycle -> next period: 2026-10-29 -> ovulation: 2026-10-15
    assert data["ovulation_date"] == "2026-10-15"
    assert data["fertile_window_start"] == "2026-10-10"
    assert data["fertile_window_end"] == "2026-10-16"
    assert data["next_period_date"] == "2026-10-29"
    assert len(data["fertility_score_by_day"]) == 7


def test_hcg_calculator_normal_doubling():
    payload = {
        "first_level": 150.0,
        "second_level": 320.0,
        "time_between": 48.0,
        "time_unit": "hours",
    }
    response = client.post("/api/v1/calculators/hcg", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_increasing"] is True
    assert data["doubling_time_hours"] is not None
    assert 40.0 < data["doubling_time_hours"] < 50.0
    assert data["increase_48h_percent"] > 100.0


def test_pregnancy_test_calculator():
    payload = {
        "method": "last_period",
        "date": "2026-10-01",
        "cycle_length": 28,
    }
    response = client.post("/api/v1/calculators/pregnancy-test", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Recommended test date = LMP + 28 days = 2026-10-29
    assert data["recommended_test_date"] == "2026-10-29"
    assert data["early_test_date"] == "2026-10-25"


def test_menstrual_cycle_calculator():
    payload = {
        "last_period_date": "2026-10-01",
        "period_duration": 5,
        "cycle_length": 28,
    }
    response = client.post("/api/v1/calculators/menstrual-cycle", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["phases"]) == 4
    phase_names = [p["name"] for p in data["phases"]]
    assert "Menstrual Phase" in phase_names
    assert "Follicular Phase" in phase_names
    assert "Ovulation Phase" in phase_names
    assert "Luteal Phase" in phase_names


def test_period_calculator():
    payload = {
        "last_period_date": "2026-10-01",
        "period_duration": 5,
        "cycle_length": 30,
        "forecast_months": 3,
    }
    response = client.post("/api/v1/calculators/period", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["predicted_cycles"]) == 3
    assert data["next_period_start"] == "2026-10-31"


def test_implantation_calculator():
    payload = {
        "method": "od",
        "date": "2026-10-14",
        "cycle_length": 28,
    }
    response = client.post("/api/v1/calculators/implantation", json=payload)
    assert response.status_code == 200
    data = response.json()
    # 6 to 10 days post ovulation = Oct 20 to Oct 24
    assert data["implantation_window_start"] == "2026-10-20"
    assert data["implantation_window_end"] == "2026-10-24"
    assert data["earliest_pregnancy_test_date"] == "2026-10-28"


def test_pregnancy_weeks_to_months_calculator():
    payload = {"weeks": 16, "days": 2}
    response = client.post("/api/v1/calculators/pregnancy-weeks-to-months", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["weeks"] == 16
    assert data["current_month"] == 4
    assert data["current_trimester"] == 2
    assert "Second Trimester" in data["trimester_name"]
    assert data["percentage_completed"] > 0


def test_due_date_calculator():
    payload = {
        "method": "last_period",
        "date": "2026-01-01",
        "cycle_length": 28,
    }
    response = client.post("/api/v1/calculators/due-date", json=payload)
    assert response.status_code == 200
    data = response.json()
    # 2026-01-01 + 280 days = 2026-10-08
    assert data["estimated_due_date"] == "2026-10-08"
    assert len(data["milestones"]) >= 5


def test_ivf_due_date_calculator():
    payload = {
        "date": "2026-10-01",
        "transfer_type": "tr-2",  # Day 5 Blastocyst
    }
    response = client.post("/api/v1/calculators/ivf-due-date", json=payload)
    assert response.status_code == 200
    data = response.json()
    # 2026-10-01 + 261 days = 2027-06-19
    assert data["estimated_due_date"] == "2027-06-19"
    assert "Day 5" in data["transfer_type_label"]


def test_due_date_by_ultrasound():
    payload = {
        "ultrasound_date": "2026-10-01",
        "weeks": 10,
        "days": 0,
    }
    response = client.post("/api/v1/calculators/due-date-by-ultrasound", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Scan at 10 weeks (70 days) -> EDD = 2026-10-01 + (280 - 70) days = 2026-10-01 + 210 days = 2027-04-29
    assert data["estimated_due_date"] == "2027-04-29"


if __name__ == "__main__":
    tests = [
        test_calculator_catalog,
        test_ovulation_calculator,
        test_hcg_calculator_normal_doubling,
        test_pregnancy_test_calculator,
        test_menstrual_cycle_calculator,
        test_period_calculator,
        test_implantation_calculator,
        test_pregnancy_weeks_to_months_calculator,
        test_due_date_calculator,
        test_ivf_due_date_calculator,
        test_due_date_by_ultrasound,
    ]
    for t in tests:
        t()
        print(f"✓ {t.__name__} passed")
    print(f"\nAll {len(tests)} calculator tests passed successfully!")
