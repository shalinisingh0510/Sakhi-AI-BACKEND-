"""Service for calculating Energy Expenditure (BMR/TDEE) based on Phase 6/7 rules."""

from __future__ import annotations

from datetime import date
from typing import Tuple

from app.models.health_profile import HealthProfile
from app.schemas.energy import CalculationStatus


class EnergyExpenditureService:
    """Stateless service for calculating Basal Metabolic Rate (BMR) and 
    Total Daily Energy Expenditure (TDEE).
    """

    @staticmethod
    def calculate_age(dob: date, target_date: date | None = None) -> int:
        if target_date is None:
            target_date = date.today()
        return target_date.year - dob.year - ((target_date.month, target_date.day) < (dob.month, dob.day))

    @staticmethod
    def calculate_bmr(profile: HealthProfile, target_date: date | None = None) -> Tuple[float | None, str]:
        """Calculate BMR using Mifflin-St Jeor.
        
        Returns:
            Tuple[BMR_value or None, CalculationStatus]
        """
        age = EnergyExpenditureService.calculate_age(profile.date_of_birth, target_date)
        
        # Teen gating (14-17)
        if age < 18:
            return None, CalculationStatus.TEEN_RESTRICTED
            
        # Data gating
        if not profile.weight_kg or not profile.height_cm or not profile.biological_sex:
            return None, CalculationStatus.INSUFFICIENT_DATA
            
        weight = profile.weight_kg
        height = profile.height_cm
        sex = profile.biological_sex.upper()
        
        if sex not in ("MALE", "FEMALE"):
            return None, CalculationStatus.INSUFFICIENT_DATA
            
        # Mifflin-St Jeor
        # Men: (10 × weight in kg) + (6.25 × height in cm) - (5 × age in years) + 5
        # Women: (10 × weight in kg) + (6.25 × height in cm) - (5 × age in years) - 161
        base = (10 * weight) + (6.25 * height) - (5 * age)
        
        if sex == "MALE":
            bmr = base + 5
        else:
            bmr = base - 161
            
        return round(bmr, 2), CalculationStatus.SUCCESS

    @staticmethod
    def calculate_tdee_baseline(profile: HealthProfile, target_date: date | None = None) -> Tuple[float | None, str]:
        """Calculate the baseline expenditure without active exercise logging.
        Since we log exercise separately, we multiply BMR by 1.2 (Sedentary/BMR baseline) 
        to account for NEAT (Non-Exercise Activity Thermogenesis) and TEF (Thermic Effect of Food).
        We do NOT multiply by higher activity factors here to avoid double counting active exercise.
        """
        bmr, status = EnergyExpenditureService.calculate_bmr(profile, target_date)
        if status != CalculationStatus.SUCCESS or bmr is None:
            return None, status
            
        # Baseline TDEE (Sedentary multiplier) = BMR * 1.2
        baseline_tdee = bmr * 1.2
        return round(baseline_tdee, 2), CalculationStatus.SUCCESS
