import pytest
from datetime import date
from app.services.energy_expenditure_service import EnergyExpenditureService
from app.schemas.energy import CalculationStatus

class MockProfile:
    def __init__(self, dob, weight=65, height=160, sex="FEMALE"):
        self.date_of_birth = dob
        self.weight_kg = weight
        self.height_cm = height
        self.biological_sex = sex

def test_teen_restriction():
    # 15 year old
    dob = date.today().replace(year=date.today().year - 15)
    profile = MockProfile(dob=dob)
    bmr, status = EnergyExpenditureService.calculate_bmr(profile)
    assert bmr is None
    assert status == CalculationStatus.TEEN_RESTRICTED

def test_insufficient_data():
    # Adult with missing weight
    dob = date.today().replace(year=date.today().year - 25)
    profile = MockProfile(dob=dob, weight=None)
    bmr, status = EnergyExpenditureService.calculate_bmr(profile)
    assert bmr is None
    assert status == CalculationStatus.INSUFFICIENT_DATA

    # Adult with missing height
    profile2 = MockProfile(dob=dob, height=None)
    bmr2, status2 = EnergyExpenditureService.calculate_bmr(profile2)
    assert bmr2 is None
    assert status2 == CalculationStatus.INSUFFICIENT_DATA

def test_valid_adult_bmr():
    # 25 year old female, 65kg, 160cm
    dob = date.today().replace(year=date.today().year - 25)
    profile = MockProfile(dob=dob, weight=65, height=160, sex="FEMALE")
    bmr, status = EnergyExpenditureService.calculate_bmr(profile)
    assert status == CalculationStatus.SUCCESS
    assert bmr is not None
    # 10*65 + 6.25*160 - 5*25 - 161
    # 650 + 1000 - 125 - 161 = 1364
    assert bmr == 1364.0
