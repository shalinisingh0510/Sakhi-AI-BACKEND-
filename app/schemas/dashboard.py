from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date

class DashboardProfileSnapshot(BaseModel):
    is_complete: bool
    mode: str  # "teen" or "adult"
    
class TodaySnapshot(BaseModel):
    check_in_completed: bool
    mood: Optional[str] = None
    energy: Optional[str] = None
    symptoms_count: int = 0
    symptoms: list[dict] = []

class CycleSnapshot(BaseModel):
    cycle_day: Optional[int] = None
    next_period: Optional[date] = None
    ovulation: Optional[date] = None
    confidence: Optional[str] = None

class WellnessTrendsSnapshot(BaseModel):
    symptom_days_last_30: int = 0
    check_ins_last_7: int = 0
    check_ins_last_30: int = 0
    # Additional simple stats could go here

class TrackingStatusSnapshot(BaseModel):
    check_in_status: str
    cycle_status: str
    symptoms_status: str

class WellnessDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    date: date
    profile: DashboardProfileSnapshot
    today: TodaySnapshot
    cycle: CycleSnapshot
    trends: WellnessTrendsSnapshot
    tracking_status: TrackingStatusSnapshot
