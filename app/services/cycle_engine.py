"""Deterministic Menstrual Cycle Calculation Engine.

IMPORTANT:
  * This module contains ONLY pure calculation functions.
  * It MUST NOT import any database, FastAPI, or AI modules.
  * It MUST NOT call Gemini, Groq, OpenAI, or any LLM.
  * All functions must be independently unit-testable.
  * All outputs are ESTIMATES. Never claim clinical certainty.

Algorithm version: cycle-v1

Cycle-length semantics:
  Cycle length = number of calendar days from the first day of period N
                 to the first day of period N+1.
  Example: Period 1 starts Jan 1, Period 2 starts Jan 29 → cycle = 28 days.

Period-duration semantics:
  Duration = (end_date - start_date).days + 1
  Example: Aug 1 → Aug 5 = 5 days (not 4).

Current cycle day:
  Day 1 = the day the current period started.
  Example: period started Aug 10, today Aug 23 → cycle day 14.

Ovulation estimate:
  Ovulation ≈ next_period_estimate - luteal_phase_days (default 14).
  This is the standard calendar method — not a clinical measurement.

Fertile window:
  Typically ovulation - 5 days through ovulation + 1 day (6-day window).
  This is an educational estimate only — NOT a reliable contraception method.

Confidence classification:
  0 periods  → no estimate
  1 period   → LOW
  2 periods  → LOW
  3–4 cycles → MEDIUM if variability < 7 days else LOW
  5+ cycles  → HIGH if var < 5 days, MEDIUM if var < 10, else LOW

Irregularity detection:
  If max(cycle_lengths) - min(cycle_lengths) > threshold_days (default 7),
  report an irregularity observation (NOT a diagnosis).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

ALGORITHM_VERSION = "cycle-v1"
DEFAULT_LUTEAL_PHASE_DAYS = 14
DEFAULT_FERTILE_WINDOW_DAYS_BEFORE = 5
DEFAULT_FERTILE_WINDOW_DAYS_AFTER = 1
IRREGULARITY_THRESHOLD_DAYS = 7

# Minimum cycles for confidence levels
CONFIDENCE_LOW_MIN = 1
CONFIDENCE_MEDIUM_MIN = 3
CONFIDENCE_HIGH_MIN = 5


# ---------------------------------------------------------------------------
# Data classes (pure Python, no SQLAlchemy)
# ---------------------------------------------------------------------------


@dataclass
class CycleRecord:
    """Lightweight representation of a completed cycle for engine input."""

    cycle_start_date: date
    cycle_end_date: Optional[date]
    cycle_length_days: Optional[int]
    period_duration_days: Optional[int]
    is_complete: bool


@dataclass
class PeriodRecord:
    """Lightweight representation of a period log for engine input."""

    start_date: date
    end_date: Optional[date]


@dataclass
class EstimatedDate:
    date: date
    confidence: str  # LOW | MEDIUM | HIGH
    algorithm_version: str = ALGORITHM_VERSION


@dataclass
class EstimatedWindow:
    start: date
    end: date
    confidence: str
    algorithm_version: str = ALGORITHM_VERSION


@dataclass
class CurrentCycleSummary:
    current_cycle_day: Optional[int]
    latest_period_start: Optional[date]
    data_quality: str  # NO_DATA | INSUFFICIENT | LIMITED | MODERATE | GOOD
    completed_cycles_count: int
    estimated_next_period: Optional[EstimatedDate]
    estimated_ovulation: Optional[EstimatedDate]
    estimated_fertile_window: Optional[EstimatedWindow]
    irregularity_observation: Optional[str]


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------


def calculate_cycle_length(start1: date, start2: date) -> int:
    """Number of calendar days from period start1 to period start2.

    Args:
        start1: First day of cycle N.
        start2: First day of cycle N+1.

    Returns:
        Integer number of days. Raises ValueError if start2 <= start1.
    """
    if start2 <= start1:
        raise ValueError(
            f"start2 ({start2}) must be after start1 ({start1}) to calculate cycle length."
        )
    return (start2 - start1).days


def calculate_period_duration(start: date, end: Optional[date]) -> Optional[int]:
    """Calculate period duration in days (inclusive of both endpoints).

    Args:
        start: First day of the period.
        end: Last day of the period. If None, duration is unknown.

    Returns:
        Number of days (int) or None if end date is missing.
        Example: Aug 1 → Aug 5 = 5 days.
    """
    if end is None:
        return None
    if end < start:
        raise ValueError(f"end ({end}) cannot be before start ({start}).")
    return (end - start).days + 1


def calculate_current_cycle_day(latest_start: date, today: Optional[date] = None) -> int:
    """Calculate the current day of the active cycle (Day 1 = period start).

    Args:
        latest_start: Start date of the most recent period.
        today: Date to use as 'today' (defaults to date.today()).

    Returns:
        Positive integer. Day 1 = the period start date itself.
    """
    if today is None:
        today = date.today()
    if today < latest_start:
        raise ValueError("today cannot be before latest_start.")
    return (today - latest_start).days + 1


def calculate_average_cycle_length(cycles: list[CycleRecord]) -> Optional[float]:
    """Arithmetic mean of completed cycle lengths.

    Only uses cycles where is_complete=True and cycle_length_days is not None.
    Does NOT silently exclude outliers (see spec §20).

    Args:
        cycles: List of CycleRecord objects.

    Returns:
        Mean cycle length in days, or None if no valid data.
    """
    lengths = [
        int(c.cycle_length_days)
        for c in cycles
        if c.is_complete and c.cycle_length_days is not None
    ]
    if not lengths:
        return None
    return statistics.mean(lengths)


def calculate_cycle_variability(cycles: list[CycleRecord]) -> Optional[float]:
    """Calculate cycle-length variability (max - min of completed cycles).

    Args:
        cycles: List of CycleRecord objects.

    Returns:
        Variability in days (max_length - min_length), or None if < 2 cycles.
    """
    lengths = [
        int(c.cycle_length_days)
        for c in cycles
        if c.is_complete and c.cycle_length_days is not None
    ]
    if len(lengths) < 2:
        return None
    return float(max(lengths) - min(lengths))


def classify_confidence(
    n_cycles: int, variability: Optional[float]
) -> Optional[str]:
    """Return confidence classification based on data quantity and consistency.

    Returns None if there is insufficient data for any estimate.

    Classification rules:
      0 cycles            → None (no estimate possible)
      1–2 cycles          → LOW
      3–4 cycles:
        variability < 7d  → MEDIUM
        otherwise         → LOW
      5+ cycles:
        variability < 5d  → HIGH
        variability < 10d → MEDIUM
        otherwise         → LOW
    """
    if n_cycles < CONFIDENCE_LOW_MIN:
        return None  # No estimate
    if n_cycles < CONFIDENCE_MEDIUM_MIN:
        return "LOW"
    if n_cycles < CONFIDENCE_HIGH_MIN:
        # 3–4 cycles
        if variability is None or variability < IRREGULARITY_THRESHOLD_DAYS:
            return "MEDIUM"
        return "LOW"
    # 5+ cycles
    if variability is None:
        return "MEDIUM"
    if variability < 5:
        return "HIGH"
    if variability < 10:
        return "MEDIUM"
    return "LOW"


def calculate_data_quality(n_period_logs: int, n_completed_cycles: int) -> str:
    """Return a DataQuality classification string."""
    if n_period_logs == 0:
        return "NO_DATA"
    if n_completed_cycles == 0:
        return "INSUFFICIENT"
    if n_completed_cycles < 2:
        return "LIMITED"
    if n_completed_cycles < 5:
        return "MODERATE"
    return "GOOD"


def detect_irregularity(
    cycles: list[CycleRecord],
    threshold_days: int = IRREGULARITY_THRESHOLD_DAYS,
) -> bool:
    """Return True if recent cycle variability exceeds the threshold.

    This is an observation, NOT a clinical diagnosis.
    The threshold is based on publicly available cycle-tracking guidelines.

    Args:
        cycles: List of CycleRecord objects. Should be recent (e.g. last 6).
        threshold_days: Variability threshold. Default 7 days.

    Returns:
        True if max_cycle_length - min_cycle_length > threshold_days.
        False if insufficient data (< 2 completed cycles).
    """
    variability = calculate_cycle_variability(cycles)
    if variability is None:
        return False
    return variability > threshold_days


def estimate_next_period(
    latest_start: date,
    average_cycle_length: float,
) -> EstimatedDate:
    """Estimate the start of the next period.

    next_period = latest_start + round(average_cycle_length)

    Args:
        latest_start: Start date of the most recent period.
        average_cycle_length: Mean cycle length in days.

    Returns:
        EstimatedDate — an estimate, not a guaranteed date.
    """
    delta = timedelta(days=round(average_cycle_length))
    return EstimatedDate(
        date=latest_start + delta,
        confidence="__PLACEHOLDER__",  # Set by caller using classify_confidence()
        algorithm_version=ALGORITHM_VERSION,
    )


def estimate_ovulation(
    next_period_estimate: date,
    luteal_phase_days: int = DEFAULT_LUTEAL_PHASE_DAYS,
) -> EstimatedDate:
    """Estimate ovulation date using the standard luteal-phase calendar method.

    ovulation_estimate = next_period_estimate - luteal_phase_days

    NOTE: This is a calendar estimate only. It does NOT confirm ovulation
    has occurred or will occur. Do NOT market this as a contraception method.

    Args:
        next_period_estimate: Estimated start of next period.
        luteal_phase_days: Assumed luteal phase length (default 14 days).

    Returns:
        EstimatedDate with confidence set by caller.
    """
    return EstimatedDate(
        date=next_period_estimate - timedelta(days=luteal_phase_days),
        confidence="__PLACEHOLDER__",
        algorithm_version=ALGORITHM_VERSION,
    )


def estimate_fertile_window(
    ovulation_estimate: date,
    days_before: int = DEFAULT_FERTILE_WINDOW_DAYS_BEFORE,
    days_after: int = DEFAULT_FERTILE_WINDOW_DAYS_AFTER,
) -> EstimatedWindow:
    """Estimate the fertile window (typically 6 days around ovulation).

    window = [ovulation - days_before, ovulation + days_after]

    DISCLAIMER: Cycle-based estimates can be uncertain and should NOT be used
    as a reliable method of contraception. This is for educational awareness only.

    Args:
        ovulation_estimate: Estimated ovulation date.
        days_before: Days before ovulation (default 5).
        days_after: Days after ovulation (default 1).

    Returns:
        EstimatedWindow with confidence set by caller.
    """
    return EstimatedWindow(
        start=ovulation_estimate - timedelta(days=days_before),
        end=ovulation_estimate + timedelta(days=days_after),
        confidence="__PLACEHOLDER__",
        algorithm_version=ALGORITHM_VERSION,
    )


# ---------------------------------------------------------------------------
# High-level composite function
# ---------------------------------------------------------------------------


def build_current_cycle_summary(
    period_logs: list[PeriodRecord],
    completed_cycles: list[CycleRecord],
    today: Optional[date] = None,
    include_advanced_features: bool = False,  # True only for 18+ users
) -> CurrentCycleSummary:
    """Build the full current-cycle summary used by the API response.

    Args:
        period_logs: All period logs, sorted by start_date ascending.
        completed_cycles: All completed cycles, sorted by start_date ascending.
        today: Date to use as today (defaults to date.today()).
        include_advanced_features: Whether to compute ovulation/fertile window.
            Set to True only for users eligible via HealthFeaturePolicy.can_use_advanced_reproductive_features().

    Returns:
        CurrentCycleSummary with all available estimates populated.
        Fields with insufficient data are set to None.
    """
    if today is None:
        today = date.today()

    n_logs = len(period_logs)
    n_completed = len(completed_cycles)
    data_quality = calculate_data_quality(n_logs, n_completed)

    if n_logs == 0:
        return CurrentCycleSummary(
            current_cycle_day=None,
            latest_period_start=None,
            data_quality=data_quality,
            completed_cycles_count=0,
            estimated_next_period=None,
            estimated_ovulation=None,
            estimated_fertile_window=None,
            irregularity_observation=None,
        )

    latest_start = max(log.start_date for log in period_logs)
    current_day = calculate_current_cycle_day(latest_start, today)

    # Average and variability
    avg_length = calculate_average_cycle_length(completed_cycles)
    variability = calculate_cycle_variability(completed_cycles)
    confidence_str = classify_confidence(n_completed, variability)

    # Irregularity observation
    is_irregular = detect_irregularity(completed_cycles)
    irregularity_obs: Optional[str] = (
        "Your recent cycles have varied more than usual. Estimates may be less predictable."
        if is_irregular
        else None
    )

    # Build next-period estimate if possible
    estimated_next: Optional[EstimatedDate] = None
    if avg_length is not None and confidence_str is not None:
        estimated_next = estimate_next_period(latest_start, avg_length)
        estimated_next.confidence = confidence_str

    # Build ovulation/fertile window (18+ only)
    estimated_ovulation: Optional[EstimatedDate] = None
    estimated_fertile: Optional[EstimatedWindow] = None
    if include_advanced_features and estimated_next is not None:
        ov = estimate_ovulation(estimated_next.date)
        ov.confidence = confidence_str  # type: ignore[assignment]
        estimated_ovulation = ov

        fw = estimate_fertile_window(ov.date)
        fw.confidence = confidence_str  # type: ignore[assignment]
        estimated_fertile = fw

    return CurrentCycleSummary(
        current_cycle_day=current_day,
        latest_period_start=latest_start,
        data_quality=data_quality,
        completed_cycles_count=n_completed,
        estimated_next_period=estimated_next,
        estimated_ovulation=estimated_ovulation,
        estimated_fertile_window=estimated_fertile,
        irregularity_observation=irregularity_obs,
    )


def rebuild_cycles_from_period_logs(
    period_logs: list[PeriodRecord],
) -> list[CycleRecord]:
    """Derive MenstrualCycle records from a sorted list of PeriodRecords.

    This function implements the raw→derived boundary.
    It must be called after any period log mutation.

    Args:
        period_logs: All period logs for a profile, sorted by start_date ascending.

    Returns:
        List of CycleRecord objects to be persisted (replacing existing ones).
    """
    if not period_logs:
        return []

    sorted_logs = sorted(period_logs, key=lambda p: p.start_date)
    cycles: list[CycleRecord] = []

    for i, log in enumerate(sorted_logs):
        is_last = i == len(sorted_logs) - 1
        next_log = sorted_logs[i + 1] if not is_last else None

        if next_log is not None:
            # Complete cycle
            cycle_length = calculate_cycle_length(log.start_date, next_log.start_date)
            cycle_end = next_log.start_date - timedelta(days=1)
            period_dur = calculate_period_duration(log.start_date, log.end_date)
            cycles.append(
                CycleRecord(
                    cycle_start_date=log.start_date,
                    cycle_end_date=cycle_end,
                    cycle_length_days=cycle_length,
                    period_duration_days=period_dur,
                    is_complete=True,
                )
            )
        else:
            # Current (incomplete) cycle
            period_dur = calculate_period_duration(log.start_date, log.end_date)
            cycles.append(
                CycleRecord(
                    cycle_start_date=log.start_date,
                    cycle_end_date=None,
                    cycle_length_days=None,
                    period_duration_days=period_dur,
                    is_complete=False,
                )
            )

    return cycles
