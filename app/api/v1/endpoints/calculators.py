from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException, status

from app.schemas.calculators import (
    CalculatorCatalogResponse,
    CalculatorCategory,
    OvulationRequest,
    OvulationResponse,
    HcgRequest,
    HcgResponse,
    PregnancyTestRequest,
    PregnancyTestResponse,
    MenstrualCycleRequest,
    MenstrualCycleResponse,
    PeriodRequest,
    PeriodResponse,
    ImplantationRequest,
    ImplantationResponse,
    PregnancyWeeksToMonthsRequest,
    PregnancyWeeksToMonthsResponse,
    DueDateRequest,
    DueDateResponse,
    IvfDueDateRequest,
    IvfDueDateResponse,
    UltrasoundDueDateRequest,
    UltrasoundDueDateResponse,
)
from app.services.calculators import CalculatorService

router = APIRouter(prefix="/calculators", tags=["Calculators & Health Tools"])


@router.get(
    "/catalog",
    response_model=CalculatorCatalogResponse,
    summary="Get all available calculators and health tools",
    description="Returns metadata, categories, slugs, and details for all Flo Health style calculators.",
)
def get_catalog() -> CalculatorCatalogResponse:
    catalog = CalculatorService.get_catalog()
    categories = [c.value for c in CalculatorCategory]
    return CalculatorCatalogResponse(calculators=catalog, categories=categories)


@router.post(
    "/ovulation",
    response_model=OvulationResponse,
    summary="Ovulation and Fertile Window Calculator",
    description="Calculate likely ovulation day and 6-day fertile window based on LMP and cycle length.",
)
def calculate_ovulation(payload: OvulationRequest) -> OvulationResponse:
    try:
        return CalculatorService.calculate_ovulation(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/hcg",
    response_model=HcgResponse,
    summary="Beta hCG Doubling Time Calculator",
    description="Calculates hCG doubling time in hours and days, and expected 24h & 48h percentage increase.",
)
def calculate_hcg(payload: HcgRequest) -> HcgResponse:
    try:
        return CalculatorService.calculate_hcg(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/pregnancy-test",
    response_model=PregnancyTestResponse,
    summary="Pregnancy Test Calculator",
    description="Calculates the most reliable date to take an early home pregnancy test.",
)
def calculate_pregnancy_test(payload: PregnancyTestRequest) -> PregnancyTestResponse:
    try:
        return CalculatorService.calculate_pregnancy_test(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/menstrual-cycle",
    response_model=MenstrualCycleResponse,
    summary="Menstrual Cycle & Phases Calculator",
    description="Breaks down the 4 biological phases of the cycle with hormonal, emotional and physical details.",
)
def calculate_menstrual_cycle(payload: MenstrualCycleRequest) -> MenstrualCycleResponse:
    try:
        return CalculatorService.calculate_menstrual_cycle(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/period",
    response_model=PeriodResponse,
    summary="Period Predictor Calculator",
    description="Predicts the upcoming 3 to 6 months of menstrual periods and PMS windows.",
)
def calculate_period(payload: PeriodRequest) -> PeriodResponse:
    try:
        return CalculatorService.calculate_period(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/implantation",
    response_model=ImplantationResponse,
    summary="Implantation Window Calculator",
    description="Determines the 6-10 DPO window when embryonic implantation takes place.",
)
def calculate_implantation(payload: ImplantationRequest) -> ImplantationResponse:
    try:
        return CalculatorService.calculate_implantation(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/pregnancy-weeks-to-months",
    response_model=PregnancyWeeksToMonthsResponse,
    summary="Pregnancy Weeks to Months Converter",
    description="Converts pregnancy weeks into corresponding medical months and trimester milestones.",
)
def calculate_pregnancy_weeks_to_months(payload: PregnancyWeeksToMonthsRequest) -> PregnancyWeeksToMonthsResponse:
    try:
        return CalculatorService.calculate_pregnancy_weeks_to_months(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/due-date",
    response_model=DueDateResponse,
    summary="Pregnancy Due Date Calculator",
    description="Calculates Estimated Due Date (EDD) by LMP or conception date and gestational age.",
)
def calculate_due_date(payload: DueDateRequest) -> DueDateResponse:
    try:
        return CalculatorService.calculate_due_date(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/ivf-due-date",
    response_model=IvfDueDateResponse,
    summary="IVF and FET Due Date Calculator",
    description="Calculates due date accurately following Day 3, Day 5 blastocyst, or egg retrieval transfer.",
)
def calculate_ivf_due_date(payload: IvfDueDateRequest) -> IvfDueDateResponse:
    try:
        return CalculatorService.calculate_ivf_due_date(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/due-date-by-ultrasound",
    response_model=UltrasoundDueDateResponse,
    summary="Due Date Calculator by Ultrasound",
    description="Calculates due date using crown-rump length / gestational age determined during ultrasound scan.",
)
def calculate_due_date_by_ultrasound(payload: UltrasoundDueDateRequest) -> UltrasoundDueDateResponse:
    try:
        return CalculatorService.calculate_ultrasound_due_date(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
