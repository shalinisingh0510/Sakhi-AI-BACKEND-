import pytest
from datetime import date, timedelta
from app.services.cycle_engine import (
    calculate_cycle_length,
    calculate_period_duration,
    calculate_current_cycle_day,
    calculate_average_cycle_length,
    calculate_cycle_variability,
    detect_irregularity,
    estimate_next_period,
    estimate_ovulation,
    estimate_fertile_window,
    classify_confidence,
    rebuild_cycles_from_period_logs,
    CycleRecord,
    PeriodRecord,
)

# Test 1: Cycle Length
def test_calculate_cycle_length():
    start1 = date(2026, 1, 1)
    start2 = date(2026, 1, 29)
    assert calculate_cycle_length(start1, start2) == 28

def test_calculate_cycle_length_invalid():
    with pytest.raises(ValueError):
        calculate_cycle_length(date(2026, 1, 29), date(2026, 1, 1))

# Test 2: Period Duration
def test_calculate_period_duration():
    start = date(2026, 1, 1)
    end = date(2026, 1, 5)
    assert calculate_period_duration(start, end) == 5

def test_calculate_period_duration_missing_end():
    assert calculate_period_duration(date(2026, 1, 1), None) is None

# Test 3: Current Cycle Day
def test_calculate_current_cycle_day():
    latest_start = date(2026, 8, 10)
    today = date(2026, 8, 23)
    assert calculate_current_cycle_day(latest_start, today) == 14

# Test 4-7: Confidence Classification
def test_classify_confidence():
    assert classify_confidence(0, None) is None
    assert classify_confidence(1, None) == "LOW"
    assert classify_confidence(2, 2.0) == "LOW"
    assert classify_confidence(4, 5.0) == "MEDIUM"
    assert classify_confidence(4, 8.0) == "LOW"
    assert classify_confidence(6, 4.0) == "HIGH"
    assert classify_confidence(6, 8.0) == "MEDIUM"
    assert classify_confidence(6, 15.0) == "LOW"

# Test 8: Averages and Variability
def test_average_and_variability():
    cycles = [
        CycleRecord(date(2026, 1, 1), date(2026, 1, 28), 28, 5, True),
        CycleRecord(date(2026, 1, 29), date(2026, 2, 28), 31, 5, True),
        CycleRecord(date(2026, 3, 1), date(2026, 3, 30), 30, 4, True),
    ]
    assert calculate_average_cycle_length(cycles) == pytest.approx(29.66, 0.01)
    assert calculate_cycle_variability(cycles) == 3.0
    assert not detect_irregularity(cycles)

def test_irregularity_detection():
    cycles = [
        CycleRecord(date(2026, 1, 1), None, 28, 5, True),
        CycleRecord(date(2026, 1, 29), None, 45, 5, True), # High variability
    ]
    assert detect_irregularity(cycles)

# Test 9: Estimates
def test_estimates():
    latest = date(2026, 8, 10)
    avg_cycle = 28.0
    
    # Next Period
    est_next = estimate_next_period(latest, avg_cycle)
    assert est_next.date == date(2026, 9, 7)
    
    # Ovulation
    est_ov = estimate_ovulation(est_next.date)
    assert est_ov.date == date(2026, 8, 24)
    
    # Fertile Window
    est_fw = estimate_fertile_window(est_ov.date)
    assert est_fw.start == date(2026, 8, 19)
    assert est_fw.end == date(2026, 8, 25)

# Test 10: Rebuild Cycles
def test_rebuild_cycles():
    logs = [
        PeriodRecord(date(2026, 1, 1), date(2026, 1, 5)),
        PeriodRecord(date(2026, 1, 29), None),
    ]
    cycles = rebuild_cycles_from_period_logs(logs)
    assert len(cycles) == 2
    
    # First cycle
    assert cycles[0].is_complete
    assert cycles[0].cycle_length_days == 28
    assert cycles[0].cycle_end_date == date(2026, 1, 28)
    
    # Second cycle
    assert not cycles[1].is_complete
    assert cycles[1].cycle_length_days is None
    assert cycles[1].cycle_end_date is None
