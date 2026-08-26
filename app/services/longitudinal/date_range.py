"""Utilities for standardized longitudinal time windows."""

from datetime import date, timedelta
from typing import Literal

TimeRange = Literal["7d", "14d", "30d", "60d", "90d", "6mo"]

def get_date_range(target_date: date, time_range: TimeRange) -> tuple[date, date]:
    """Return (start_date, end_date) for a given time window ending on target_date."""
    if time_range == "7d":
        start_date = target_date - timedelta(days=7)
    elif time_range == "14d":
        start_date = target_date - timedelta(days=14)
    elif time_range == "30d":
        start_date = target_date - timedelta(days=30)
    elif time_range == "60d":
        start_date = target_date - timedelta(days=60)
    elif time_range == "90d":
        start_date = target_date - timedelta(days=90)
    elif time_range == "6mo":
        start_date = target_date - timedelta(days=180)
    else:
        # Default to 30 days
        start_date = target_date - timedelta(days=30)
        
    return start_date, target_date
