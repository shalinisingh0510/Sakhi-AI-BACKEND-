from __future__ import annotations
from datetime import date as dt_date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CalculatorCategory(str, Enum):
    FERTILITY = "fertility"
    PREGNANCY = "pregnancy"
    CYCLE = "cycle"
    CLINICAL = "clinical"


class CalculatorMeta(BaseModel):
    id: str
    title: str
    short_title: str
    slug: str
    category: CalculatorCategory
    description: str
    icon: str
    badge: Optional[str] = None
    featured: bool = False


class CalculatorCatalogResponse(BaseModel):
    calculators: List[CalculatorMeta]
    categories: List[str]


# 1. Ovulation Calculator
class OvulationRequest(BaseModel):
    last_period_date: dt_date = Field(..., description="First day of last menstrual period")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days (20-45)")


class OvulationResponse(BaseModel):
    ovulation_date: dt_date
    fertile_window_start: dt_date
    fertile_window_end: dt_date
    next_period_date: dt_date
    cycle_length: int
    most_fertile_days: List[dt_date]
    fertility_score_by_day: List[Dict[str, Any]]
    clinical_note: str


# 2. hCG Doubling Calculator
class TimeUnit(str, Enum):
    HOURS = "hours"
    DAYS = "days"


class HcgRequest(BaseModel):
    first_level: float = Field(..., gt=0, description="First hCG level in mIU/mL")
    second_level: float = Field(..., gt=0, description="Second hCG level in mIU/mL")
    time_between: float = Field(..., gt=0, description="Time between tests")
    time_unit: TimeUnit = Field(TimeUnit.DAYS, description="Time unit (hours or days)")


class HcgResponse(BaseModel):
    first_level: float
    second_level: float
    time_hours: float
    doubling_time_hours: Optional[float]
    doubling_time_days: Optional[float]
    increase_24h_percent: float
    increase_48h_percent: float
    is_increasing: bool
    status: str
    clinical_interpretation: str
    chart_reference: List[Dict[str, Any]]


# 3. Pregnancy Test Calculator
class PregnancyTestMethod(str, Enum):
    LAST_PERIOD = "last_period"
    OVULATION = "ovulation"


class PregnancyTestRequest(BaseModel):
    method: PregnancyTestMethod = Field(PregnancyTestMethod.LAST_PERIOD)
    date: dt_date = Field(..., description="Date of LMP or Ovulation/Intercourse")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days")


class PregnancyTestResponse(BaseModel):
    recommended_test_date: dt_date
    early_test_date: dt_date
    days_past_ovulation: int
    days_until_recommended_test: int
    test_accuracy_today: str
    clinical_guidance: str
    timeline: List[Dict[str, Any]]


# 4. Menstrual Cycle Calculator
class MenstrualCycleRequest(BaseModel):
    last_period_date: dt_date = Field(..., description="First day of last menstrual period")
    period_duration: int = Field(5, ge=2, le=10, description="Duration of bleeding in days")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days")


class CyclePhaseInfo(BaseModel):
    name: str
    start_date: dt_date
    end_date: dt_date
    duration_days: int
    hormone_focus: str
    body_symptoms: List[str]
    energy_level: str
    wellness_tips: str


class MenstrualCycleResponse(BaseModel):
    next_period_start: dt_date
    next_period_end: dt_date
    ovulation_date: dt_date
    fertile_window_start: dt_date
    fertile_window_end: dt_date
    phases: List[CyclePhaseInfo]
    cycle_regularity_info: str


# 5. Period Calculator
class PeriodRequest(BaseModel):
    last_period_date: dt_date = Field(..., description="First day of last menstrual period")
    period_duration: int = Field(5, ge=2, le=10, description="Duration of bleeding in days")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days")
    forecast_months: int = Field(3, ge=1, le=6, description="Number of months to forecast")


class PredictedCycle(BaseModel):
    cycle_number: int
    period_start: dt_date
    period_end: dt_date
    ovulation_date: dt_date
    fertile_start: dt_date
    fertile_end: dt_date
    pms_start: dt_date


class PeriodResponse(BaseModel):
    days_until_next_period: int
    next_period_start: dt_date
    next_period_end: dt_date
    next_ovulation_date: dt_date
    predicted_cycles: List[PredictedCycle]
    summary_text: str


# 6. Implantation Calculator
class ImplantationMethod(str, Enum):
    OVULATION = "od"
    LAST_PERIOD = "lp"


class ImplantationRequest(BaseModel):
    method: ImplantationMethod = Field(ImplantationMethod.OVULATION)
    date: dt_date = Field(..., description="Ovulation date or LMP date")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days")


class ImplantationResponse(BaseModel):
    ovulation_date: dt_date
    implantation_window_start: dt_date
    implantation_window_end: dt_date
    peak_implantation_date: dt_date
    earliest_pregnancy_test_date: dt_date
    days_past_ovulation_range: str
    symptoms_guide: List[Dict[str, Any]]
    clinical_note: str


# 7. Pregnancy Weeks to Months Calculator
class PregnancyWeeksToMonthsRequest(BaseModel):
    weeks: int = Field(..., ge=1, le=42, description="Gestational weeks (1-42)")
    days: int = Field(0, ge=0, le=6, description="Extra days (0-6)")


class PregnancyWeeksToMonthsResponse(BaseModel):
    weeks: int
    days: int
    total_days: int
    current_month: int
    current_trimester: int
    trimester_name: str
    percentage_completed: float
    estimated_due_date: dt_date
    baby_size_comparison: str
    fetal_development_milestones: List[str]
    trimester_timeline: List[Dict[str, Any]]


# 8. Pregnancy Due Date Calculator
class DueDateMethod(str, Enum):
    LAST_PERIOD = "last_period"
    CONCEPTION = "conception"


class DueDateRequest(BaseModel):
    method: DueDateMethod = Field(DueDateMethod.LAST_PERIOD)
    date: dt_date = Field(..., description="LMP date or Conception date")
    cycle_length: int = Field(28, ge=20, le=45, description="Average cycle length in days")


class DueDateMilestone(BaseModel):
    milestone: str
    date: dt_date
    gestational_age: str
    description: str


class DueDateResponse(BaseModel):
    estimated_due_date: dt_date
    conception_date: dt_date
    gestational_age_weeks: int
    gestational_age_days: int
    current_trimester: int
    days_remaining: int
    percentage_progress: float
    milestones: List[DueDateMilestone]
    clinical_guideline: str


# 9. IVF Due Date Calculator
class IvfTransferType(str, Enum):
    DAY_3 = "tr-1"  # Day 3 embryo transfer (offset 17d, EDD +263d)
    DAY_5 = "tr-2"  # Day 5 blastocyst transfer (offset 19d, EDD +261d)
    DAY_6 = "tr-4"  # Day 6 blastocyst transfer (offset 20d, EDD +260d)
    RETRIEVAL = "tr-3"  # Egg retrieval / Day 0 / IUI (offset 14d, EDD +266d)


class IvfDueDateRequest(BaseModel):
    date: dt_date = Field(..., description="Date of transfer or egg retrieval")
    transfer_type: IvfTransferType = Field(IvfTransferType.DAY_5, description="Transfer type")


class IvfDueDateResponse(BaseModel):
    estimated_due_date: dt_date
    theoretical_lmp: dt_date
    gestational_age_weeks: int
    gestational_age_days: int
    days_remaining: int
    transfer_type_label: str
    milestones: List[DueDateMilestone]
    clinical_explanation: str


# 10. Due Date by Ultrasound Calculator
class UltrasoundDueDateRequest(BaseModel):
    ultrasound_date: dt_date = Field(..., description="Date ultrasound scan was performed")
    weeks: int = Field(..., ge=1, le=40, description="Gestational age weeks at scan")
    days: int = Field(0, ge=0, le=6, description="Gestational age days at scan")
    crl_mm: Optional[float] = Field(None, ge=1.0, le=90.0, description="Optional Crown-Rump Length in mm")


class UltrasoundDueDateResponse(BaseModel):
    estimated_due_date: dt_date
    estimated_conception_date: dt_date
    gestational_age_at_scan_days: int
    current_gestational_age_weeks: int
    current_gestational_age_days: int
    days_remaining: int
    acog_redating_criteria: str
    scan_insights: str
