from __future__ import annotations
import math
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

from app.schemas.calculators import (
    CalculatorMeta,
    CalculatorCategory,
    OvulationRequest,
    OvulationResponse,
    HcgRequest,
    HcgResponse,
    TimeUnit,
    PregnancyTestRequest,
    PregnancyTestResponse,
    PregnancyTestMethod,
    MenstrualCycleRequest,
    MenstrualCycleResponse,
    CyclePhaseInfo,
    PeriodRequest,
    PeriodResponse,
    PredictedCycle,
    ImplantationRequest,
    ImplantationResponse,
    ImplantationMethod,
    PregnancyWeeksToMonthsRequest,
    PregnancyWeeksToMonthsResponse,
    DueDateRequest,
    DueDateResponse,
    DueDateMethod,
    DueDateMilestone,
    IvfDueDateRequest,
    IvfDueDateResponse,
    IvfTransferType,
    UltrasoundDueDateRequest,
    UltrasoundDueDateResponse,
)

CALCULATORS_CATALOG: List[CalculatorMeta] = [
    CalculatorMeta(
        id="ovulation-calculator",
        title="Ovulation Calculator: Figure Out Your Most Fertile Days",
        short_title="Ovulation Calculator",
        slug="ovulation-calculator",
        category=CalculatorCategory.FERTILITY,
        description="Identify your likely ovulation day and 6-day fertile window to optimize conception or track your body's rhythm.",
        icon="Sparkles",
        badge="Popular",
        featured=True,
    ),
    CalculatorMeta(
        id="hcg-calculator",
        title="Beta hCG Doubling Time Calculator & Charts",
        short_title="hCG Doubling Calculator",
        slug="hcg-calculator",
        category=CalculatorCategory.CLINICAL,
        description="Track your beta-hCG blood test rise, calculate doubling time, and compare against standard early pregnancy ranges.",
        icon="Activity",
        badge="Clinical",
        featured=True,
    ),
    CalculatorMeta(
        id="pregnancy-test-calculator",
        title="Pregnancy Test Calculator: When to Take a Test",
        short_title="Pregnancy Test Calculator",
        slug="pregnancy-test-calculator",
        category=CalculatorCategory.FERTILITY,
        description="Find out the most accurate day to take a home pregnancy test based on your period or ovulation date to prevent false negatives.",
        icon="CheckCircle2",
        featured=False,
    ),
    CalculatorMeta(
        id="menstrual-cycle-calculator",
        title="Menstrual Cycle Calculator: Phases & Hormone Rhythm",
        short_title="Menstrual Cycle Calculator",
        slug="menstrual-cycle-calculator",
        category=CalculatorCategory.CYCLE,
        description="Explore the 4 phases of your menstrual cycle — menstrual, follicular, ovulation, and luteal — and how your hormones fluctuate.",
        icon="Calendar",
        featured=True,
    ),
    CalculatorMeta(
        id="period-calculator",
        title="Period Calculator: Predict Your Next 3 Cycles",
        short_title="Period Calculator",
        slug="period-calculator",
        category=CalculatorCategory.CYCLE,
        description="Predict when your next periods will arrive, plan trips and events, and stay in tune with your personal cycle schedule.",
        icon="CalendarDays",
        badge="Essential",
        featured=True,
    ),
    CalculatorMeta(
        id="implantation-calculator",
        title="Implantation Calculator: When Does Implantation Occur?",
        short_title="Implantation Calculator",
        slug="implantation-calculator",
        category=CalculatorCategory.FERTILITY,
        description="Calculate the exact window when a fertilized egg attaches to the uterine lining and understand early implantation signs.",
        icon="HeartPulse",
        featured=False,
    ),
    CalculatorMeta(
        id="pregnancy-weeks-to-months-calculator",
        title="Pregnancy Weeks to Months Calculator: How Far Along Are You?",
        short_title="Weeks to Months Calculator",
        slug="pregnancy-weeks-to-months-calculator",
        category=CalculatorCategory.PREGNANCY,
        description="Convert pregnancy weeks into months and trimesters, track fetal size comparisons, and understand developmental milestones.",
        icon="Baby",
        featured=True,
    ),
    CalculatorMeta(
        id="due-date-calculator",
        title="Pregnancy Due Date Calculator",
        short_title="Due Date Calculator",
        slug="due-date-calculator",
        category=CalculatorCategory.PREGNANCY,
        description="Calculate your estimated due date (EDD) using your last period or conception date, and see key trimester milestones.",
        icon="Clock",
        badge="Top Tool",
        featured=True,
    ),
    CalculatorMeta(
        id="ivf-due-date-calculator",
        title="IVF and FET Due Date Calculator",
        short_title="IVF Due Date Calculator",
        slug="ivf-due-date-calculator",
        category=CalculatorCategory.CLINICAL,
        description="Calculate your accurate due date following a Day 3, Day 5 blastocyst, Day 6, or fresh/frozen embryo transfer.",
        icon="Microscope",
        badge="Specialized",
        featured=False,
    ),
    CalculatorMeta(
        id="due-date-by-ultrasound",
        title="Due Date Calculator by Ultrasound",
        short_title="Ultrasound Due Date Calculator",
        slug="due-date-by-ultrasound",
        category=CalculatorCategory.CLINICAL,
        description="Calculate your due date based on an early sonogram / ultrasound scan and understand ACOG redating criteria.",
        icon="ScanLine",
        featured=False,
    ),
]


BABY_SIZE_MAPPING = {
    1: "Microscopic blastocyst (Poppy seed)",
    2: "Sesame seed (Week 5) to Blueberry (Week 7)",
    3: "Raspberry (Week 8) to Lime / Plum (Week 12)",
    4: "Peach (Week 13) to Avocado (Week 16)",
    5: "Pomegranate (Week 17) to Banana (Week 20)",
    6: "Carrot (Week 21) to Cauliflower (Week 25)",
    7: "Eggplant (Week 26) to Butternut Squash (Week 30)",
    8: "Coconut (Week 31) to Honeydew Melon (Week 35)",
    9: "Watermelon / Pumpkin (Full Term)",
}

WEEKS_TO_MONTH_RANGES = [
    {"range": (1, 4), "month": 1, "trimester": 1, "trimester_name": "First Trimester"},
    {"range": (5, 8), "month": 2, "trimester": 1, "trimester_name": "First Trimester"},
    {"range": (9, 13), "month": 3, "trimester": 1, "trimester_name": "First Trimester"},
    {"range": (14, 17), "month": 4, "trimester": 2, "trimester_name": "Second Trimester"},
    {"range": (18, 22), "month": 5, "trimester": 2, "trimester_name": "Second Trimester"},
    {"range": (23, 27), "month": 6, "trimester": 2, "trimester_name": "Second Trimester"},
    {"range": (28, 31), "month": 7, "trimester": 3, "trimester_name": "Third Trimester"},
    {"range": (32, 35), "month": 8, "trimester": 3, "trimester_name": "Third Trimester"},
    {"range": (36, 42), "month": 9, "trimester": 3, "trimester_name": "Third Trimester"},
]


class CalculatorService:

    @staticmethod
    def get_catalog() -> List[CalculatorMeta]:
        return CALCULATORS_CATALOG

    # 1. Ovulation Calculator
    @staticmethod
    def calculate_ovulation(payload: OvulationRequest) -> OvulationResponse:
        # Flo Health logic:
        # Next period = LMP + cycle days
        # Ovulation = Next period - 14 days
        # Start fertile = Ovulation - 5 days
        # End fertile = Ovulation + 1 day
        next_period = payload.last_period_date + timedelta(days=payload.cycle_length)
        ovulation = next_period - timedelta(days=14)
        fertile_start = ovulation - timedelta(days=5)
        fertile_end = ovulation + timedelta(days=1)

        # Most fertile days: Ovulation day & day before
        most_fertile = [ovulation - timedelta(days=1), ovulation]

        # Fertility score curve by day (0 to 100%)
        # Day -5 (10%), -4 (15%), -3 (20%), -2 (28%), -1 (33%), Day 0 (30%), Day +1 (10%)
        scores = [
            {"date": fertile_start, "score": 12, "label": "Fertile (Medium)"},
            {"date": fertile_start + timedelta(days=1), "score": 18, "label": "Fertile (Medium)"},
            {"date": fertile_start + timedelta(days=2), "score": 24, "label": "High Fertility"},
            {"date": fertile_start + timedelta(days=3), "score": 32, "label": "Very High Fertility"},
            {"date": ovulation - timedelta(days=1), "score": 35, "label": "Peak Fertility (Day Before Ovulation)"},
            {"date": ovulation, "score": 30, "label": "Ovulation Day (Peak)"},
            {"date": fertile_end, "score": 10, "label": "Ovulation + 1 (Egg viable ~12-24h)"},
        ]

        clinical_note = (
            f"Based on your {payload.cycle_length}-day cycle, your luteal phase is estimated at 14 days. "
            f"Your fertile window spans 6 days because sperm can survive up to 5 days in fertile cervical mucus, "
            f"while the released egg is viable for up to 24 hours."
        )

        return OvulationResponse(
            ovulation_date=ovulation,
            fertile_window_start=fertile_start,
            fertile_window_end=fertile_end,
            next_period_date=next_period,
            cycle_length=payload.cycle_length,
            most_fertile_days=most_fertile,
            fertility_score_by_day=scores,
            clinical_note=clinical_note,
        )

    # 2. hCG Calculator
    @staticmethod
    def calculate_hcg(payload: HcgRequest) -> HcgResponse:
        # Flo Health logic:
        # if timetype == 'days': time_hours = number * 24
        # doubling_hours = time_hours / log2(second / first)
        # doubling_days = doubling_hours / 24
        # inc_24 = 100 * (2^(24 / doubling_hours) - 1)
        # inc_48 = 100 * (2^(48 / doubling_hours) - 1)
        time_hours = payload.time_between * 24.0 if payload.time_unit == TimeUnit.DAYS else payload.time_between

        if payload.first_level <= 0 or payload.second_level <= 0 or time_hours <= 0:
            raise ValueError("All levels and time between tests must be positive values.")

        ratio = payload.second_level / payload.first_level
        is_increasing = ratio > 1.0

        if ratio <= 1.0 or math.isclose(ratio, 1.0):
            # hCG didn't increase
            doubling_hours = None
            doubling_days = None
            inc_24 = 0.0
            inc_48 = 0.0
            status = "Decreasing or Plateaued"
            interpretation = (
                "Your beta-hCG level has not increased between the two draws. In a progressing early intrauterine "
                "pregnancy, hCG levels typically rise continuously. A plateau or drop requires prompt medical follow-up "
                "with your healthcare provider or OB/GYN."
            )
        else:
            doubling_hours = round(time_hours / math.log2(ratio), 2)
            doubling_days = round(doubling_hours / 24.0, 2)
            inc_24 = round(100.0 * (math.pow(2.0, 24.0 / doubling_hours) - 1.0), 1)
            inc_48 = round(100.0 * (math.pow(2.0, 48.0 / doubling_hours) - 1.0), 1)

            if doubling_hours < 72.0:
                status = "Normal Doubling (Expected Rise)"
                interpretation = (
                    f"Your hCG level doubled in approximately {doubling_hours} hours ({doubling_days} days). "
                    f"A doubling time between 48 and 72 hours is typical for progressing pregnancies under 6,000 mIU/mL."
                )
            elif doubling_hours <= 96.0:
                status = "Borderline / Slower Doubling"
                interpretation = (
                    f"Your doubling time is {doubling_hours} hours ({doubling_days} days). As hCG passes 6,000 mIU/mL, "
                    f"doubling normally slows to 96+ hours. If hCG is still under 1,200 mIU/mL, consult your physician."
                )
            else:
                status = "Prolonged Doubling Time"
                interpretation = (
                    f"Your doubling time is {doubling_hours} hours, which is longer than typical early pregnancy rates. "
                    f"Please review these results with your doctor for clinical correlation and ultrasound confirmation."
                )

        # Standard clinical reference points
        chart_reference = [
            {"gestational_weeks": "3 Weeks LMP", "typical_hCG_range": "5 - 50 mIU/mL", "expected_doubling": "30 - 48 hours"},
            {"gestational_weeks": "4 Weeks LMP", "typical_hCG_range": "5 - 426 mIU/mL", "expected_doubling": "40 - 54 hours"},
            {"gestational_weeks": "5 Weeks LMP", "typical_hCG_range": "18 - 7,340 mIU/mL", "expected_doubling": "48 - 72 hours"},
            {"gestational_weeks": "6 Weeks LMP", "typical_hCG_range": "1,080 - 56,500 mIU/mL", "expected_doubling": "72 - 96 hours"},
            {"gestational_weeks": "7 - 8 Weeks", "typical_hCG_range": "7,650 - 229,000 mIU/mL", "expected_doubling": "> 96 hours (Peaks)"},
        ]

        return HcgResponse(
            first_level=payload.first_level,
            second_level=payload.second_level,
            time_hours=round(time_hours, 1),
            doubling_time_hours=doubling_hours,
            doubling_time_days=doubling_days,
            increase_24h_percent=inc_24,
            increase_48h_percent=inc_48,
            is_increasing=is_increasing,
            status=status,
            clinical_interpretation=interpretation,
            chart_reference=chart_reference,
        )

    # 3. Pregnancy Test Calculator
    @staticmethod
    def calculate_pregnancy_test(payload: PregnancyTestRequest) -> PregnancyTestResponse:
        today = date.today()

        if payload.method == PregnancyTestMethod.LAST_PERIOD:
            # LMP method:
            # Ovulation = LMP + (cycle - 14)
            # Missed period / recommended test date = LMP + cycle
            ovulation_date = payload.date + timedelta(days=payload.cycle_length - 14)
            recommended_date = payload.date + timedelta(days=payload.cycle_length)
        else:
            # Ovulation/Conception date method:
            # Ovulation date is input date
            ovulation_date = payload.date
            recommended_date = ovulation_date + timedelta(days=14)

        # Early test date: 4 days before missed period (10 DPO)
        early_test_date = recommended_date - timedelta(days=4)

        dpo = (today - ovulation_date).days
        days_until_rec = (recommended_date - today).days

        if dpo < 9:
            accuracy = "Very Low (<25% - High risk of false negative)"
        elif dpo < 12:
            accuracy = "Moderate (50-65% on early detection test)"
        elif dpo < 14:
            accuracy = "High (85-90%)"
        else:
            accuracy = "Very High (99%+ on first morning urine)"

        guidance = (
            f"The most accurate day to test is {recommended_date.strftime('%A, %B %d, %Y')} "
            f"(the day of your expected period / 14 days post-ovulation). Urine tests measure human Chorionic "
            f"Gonadotropin (hCG), which only begins entering maternal urine 2-3 days after implantation. "
            f"Testing earlier than 10 DPO frequently yields false negative results."
        )

        timeline = [
            {"stage": "Fertilization", "dpo": 0, "date": ovulation_date, "event": "Sperm meets egg in fallopian tube"},
            {"stage": "Implantation Window", "dpo": 8, "date": ovulation_date + timedelta(days=8), "event": "Blastocyst implants into uterine wall; hCG production begins"},
            {"stage": "Early Detection Possible", "dpo": 10, "date": early_test_date, "event": "High-sensitivity tests (10 mIU/mL) may show faint positive"},
            {"stage": "Optimal Test Day (Missed Period)", "dpo": 14, "date": recommended_date, "event": "99% accuracy on standard tests (25 mIU/mL)"},
        ]

        return PregnancyTestResponse(
            recommended_test_date=recommended_date,
            early_test_date=early_test_date,
            days_past_ovulation=max(0, dpo),
            days_until_recommended_test=days_until_rec,
            test_accuracy_today=accuracy,
            clinical_guidance=guidance,
            timeline=timeline,
        )

    # 4. Menstrual Cycle Calculator
    @staticmethod
    def calculate_menstrual_cycle(payload: MenstrualCycleRequest) -> MenstrualCycleResponse:
        # Flo Health logic:
        # Next period start = LMP + cycle days
        # Next period end = Next period start + period duration
        # Ovulation = Next period start - 14 days
        # Fertile = [Ovulation - 5, Ovulation + 1]
        next_start = payload.last_period_date + timedelta(days=payload.cycle_length)
        next_end = next_start + timedelta(days=payload.period_duration - 1)
        ovulation = next_start - timedelta(days=14)
        fertile_start = ovulation - timedelta(days=5)
        fertile_end = ovulation + timedelta(days=1)

        # 4 Phases definition for the upcoming cycle:
        # 1. Menstrual: Day 1 to period_duration
        # 2. Follicular: Day 1 to Ovulation day
        # 3. Ovulation: Ovulation day (±1 day)
        # 4. Luteal: Ovulation + 1 day to Day before next period
        follicular_end = ovulation - timedelta(days=1)
        luteal_start = ovulation + timedelta(days=1)
        luteal_end = next_start + timedelta(days=payload.cycle_length - 1)

        phases = [
            CyclePhaseInfo(
                name="Menstrual Phase",
                start_date=next_start,
                end_date=next_end,
                duration_days=payload.period_duration,
                hormone_focus="Estrogen & Progesterone are at baseline low",
                body_symptoms=["Cramping", "Lower back ache", "Fatigue", "Spotting/Flow"],
                energy_level="Gentle rest, restorative yoga, internal focus",
                wellness_tips="Hydrate with iron-rich foods, magnesium warm teas, and gentle stretching.",
            ),
            CyclePhaseInfo(
                name="Follicular Phase",
                start_date=next_end + timedelta(days=1),
                end_date=follicular_end,
                duration_days=(follicular_end - next_end).days,
                hormone_focus="FSH stimulates ovarian follicles; Estrogen steadily climbs",
                body_symptoms=["Clear skin", "Higher stamina", "Rising mood and libido"],
                energy_level="High energy, creative momentum, strength workouts",
                wellness_tips="Ideal time to start new projects, schedule social engagements, and eat fresh greens.",
            ),
            CyclePhaseInfo(
                name="Ovulation Phase",
                start_date=ovulation - timedelta(days=1),
                end_date=ovulation + timedelta(days=1),
                duration_days=3,
                hormone_focus="Luteinizing Hormone (LH) surge triggers egg release; Peak Estrogen",
                body_symptoms=["Egg-white cervical fluid", "Mild pelvic twinge (mittelschmerz)", "Increased confidence"],
                energy_level="Peak physical vitality, peak communication skills",
                wellness_tips="Stay hydrated, eat antioxidant-rich berries, and leverage your peak magnetic energy.",
            ),
            CyclePhaseInfo(
                name="Luteal Phase",
                start_date=luteal_start,
                end_date=luteal_end,
                duration_days=(luteal_end - luteal_start).days + 1,
                hormone_focus="Corpus luteum secretes Progesterone; second mild estrogen wave",
                body_symptoms=["Bloating", "Breast tenderness", "Food cravings", "Mild mood shifts"],
                energy_level="Reflective, detail-oriented, winding down",
                wellness_tips="Support liver detox with cruciferous vegetables, complex carbs, and prioritize 8h sleep.",
            ),
        ]

        regularity = (
            f"Your cycle length is {payload.cycle_length} days. Normal adult menstrual cycles range from 21 to 35 days. "
            f"Consistency within 2-4 days month-to-month indicates healthy, regular ovulatory function."
        )

        return MenstrualCycleResponse(
            next_period_start=next_start,
            next_period_end=next_end,
            ovulation_date=ovulation,
            fertile_window_start=fertile_start,
            fertile_window_end=fertile_end,
            phases=phases,
            cycle_regularity_info=regularity,
        )

    # 5. Period Calculator
    @staticmethod
    def calculate_period(payload: PeriodRequest) -> PeriodResponse:
        today = date.today()
        predicted_cycles: List[PredictedCycle] = []

        current_period_start = payload.last_period_date

        # Advance to future cycles
        for i in range(1, payload.forecast_months + 1):
            cycle_start = payload.last_period_date + timedelta(days=payload.cycle_length * i)
            cycle_end = cycle_start + timedelta(days=payload.period_duration - 1)
            cycle_ovulation = cycle_start - timedelta(days=14)
            cycle_fertile_start = cycle_ovulation - timedelta(days=5)
            cycle_fertile_end = cycle_ovulation + timedelta(days=1)
            cycle_pms_start = cycle_start - timedelta(days=7)

            predicted_cycles.append(
                PredictedCycle(
                    cycle_number=i,
                    period_start=cycle_start,
                    period_end=cycle_end,
                    ovulation_date=cycle_ovulation,
                    fertile_start=cycle_fertile_start,
                    fertile_end=cycle_fertile_end,
                    pms_start=cycle_pms_start,
                )
            )

        first_predicted = predicted_cycles[0]
        days_until = (first_predicted.period_start - today).days

        summary = (
            f"Your next period is predicted to start on {first_predicted.period_start.strftime('%B %d, %Y')} "
            f"and last {payload.period_duration} days until {first_predicted.period_end.strftime('%B %d')}. "
            f"{'It starts in ' + str(days_until) + ' days.' if days_until > 0 else 'Your period is due around now.'}"
        )

        return PeriodResponse(
            days_until_next_period=days_until,
            next_period_start=first_predicted.period_start,
            next_period_end=first_predicted.period_end,
            next_ovulation_date=first_predicted.ovulation_date,
            predicted_cycles=predicted_cycles,
            summary_text=summary,
        )

    # 6. Implantation Calculator
    @staticmethod
    def calculate_implantation(payload: ImplantationRequest) -> ImplantationResponse:
        # Flo Health logic:
        # If method == 'od': ovulation = date
        # If method == 'lp': ovulation = date + cycle - 14
        # Implantation occurs 6 to 10 days post-ovulation (days: 6-10)
        # Peak implantation: 8-9 DPO
        # Earliest pregnancy test: 14 DPO
        if payload.method == ImplantationMethod.OVULATION:
            ovulation = payload.date
        else:
            ovulation = payload.date + timedelta(days=payload.cycle_length - 14)

        window_start = ovulation + timedelta(days=6)
        window_end = ovulation + timedelta(days=10)
        peak_date = ovulation + timedelta(days=9)
        test_date = ovulation + timedelta(days=14)

        symptoms = [
            {"symptom": "Light Spotting", "details": "Pinkish or light rust/brown droplet, lasts 1-2 days without clots."},
            {"symptom": "Mild Uterine Cramping", "details": "Very mild prickling or tingling sensation in lower abdomen, milder than menstrual cramps."},
            {"symptom": "Basal Body Temp Dip", "details": "A transient 1-day temperature drop followed by sustained high luteal temperatures (implantation dip)."},
            {"symptom": "Fatigue & Tenderness", "details": "Early progesterone and nascent hCG elevation leading to breast tenderness and drowsiness."},
        ]

        clinical = (
            f"Implantation most commonly occurs 8 to 9 days after ovulation, with a normal physiological window of "
            f"6 to 10 days ({window_start.strftime('%b %d')} to {window_end.strftime('%b %d')}). "
            f"About 25-30% of women experience implantation bleeding. Once the blastocyst embeds, "
            f"hCG begins entering your bloodstream, doubling every 48 hours."
        )

        return ImplantationResponse(
            ovulation_date=ovulation,
            implantation_window_start=window_start,
            implantation_window_end=window_end,
            peak_implantation_date=peak_date,
            earliest_pregnancy_test_date=test_date,
            days_past_ovulation_range="6 - 10 DPO",
            symptoms_guide=symptoms,
            clinical_note=clinical,
        )

    # 7. Pregnancy Weeks to Months Calculator
    @staticmethod
    def calculate_pregnancy_weeks_to_months(payload: PregnancyWeeksToMonthsRequest) -> PregnancyWeeksToMonthsResponse:
        total_days = payload.weeks * 7 + payload.days
        today = date.today()

        # Flo Health logic:
        # total_days = 7 * weeks + days
        # percentage = min(100, round((total_days / 280) * 100))
        # EDD = today - total_days + 280
        percentage = min(100.0, round((total_days / 280.0) * 100.0, 1))
        edd = today - timedelta(days=total_days) + timedelta(days=280)

        # Trimester and month lookup
        matched_month = 1
        matched_trimester = 1
        trimester_name = "First Trimester"

        for entry in WEEKS_TO_MONTH_RANGES:
            r_start, r_end = entry["range"]
            if r_start <= payload.weeks <= r_end:
                matched_month = entry["month"]
                matched_trimester = entry["trimester"]
                trimester_name = entry["trimester_name"]
                break

        baby_size = BABY_SIZE_MAPPING.get(matched_month, "Full Term Baby")

        milestones_map = {
            1: ["Fertilization and blastocyst migration", "Implantation into uterine lining", "Neural tube begins to form"],
            2: ["Heart begins beating (~Week 6)", "Tiny arm and leg buds appear", "Facial features start developing"],
            3: ["All vital organs formed", "Baby can open fingers into fists", "Vocal cords form; risk of miscarriage drops significantly"],
            4: ["Baby can make sucking motions", "Lanugo (fine hair) covers body", "Gender may be visible on scan"],
            5: ["You may feel first flutters (quickening)", "Vernix caseosa protects baby's delicate skin", "Baby can hear muffled sounds from outside"],
            6: ["Lungs develop surfactant pathways", "Eyes open and respond to light", "Rapid brain and nervous system growth"],
            7: ["Baby practices breathing motions", "Brain wave patterns resemble full sleep cycles", "Bones harden, though skull stays pliable"],
            8: ["Rapid weight gain (approx. 0.5 lb / week)", "Immune system receives maternal antibodies", "Baby turns head-down for delivery"],
            9: ["Full term (Weeks 37+)", "Lungs fully matured", "Ready to meet the world!"],
        }

        timeline = [
            {"trimester": 1, "name": "First Trimester", "weeks": "Weeks 1 - 13", "active": matched_trimester == 1},
            {"trimester": 2, "name": "Second Trimester", "weeks": "Weeks 14 - 27", "active": matched_trimester == 2},
            {"trimester": 3, "name": "Third Trimester", "weeks": "Weeks 28 - 40+", "active": matched_trimester == 3},
        ]

        return PregnancyWeeksToMonthsResponse(
            weeks=payload.weeks,
            days=payload.days,
            total_days=total_days,
            current_month=matched_month,
            current_trimester=matched_trimester,
            trimester_name=trimester_name,
            percentage_completed=percentage,
            estimated_due_date=edd,
            baby_size_comparison=baby_size,
            fetal_development_milestones=milestones_map.get(matched_month, []),
            trimester_timeline=timeline,
        )

    # 8. Pregnancy Due Date Calculator
    @staticmethod
    def calculate_due_date(payload: DueDateRequest) -> DueDateResponse:
        today = date.today()

        if payload.method == DueDateMethod.LAST_PERIOD:
            # Flo Health: LMP + (cycle - 28) + 280 days
            cycle_adj = payload.cycle_length - 28
            edd = payload.date + timedelta(days=280 + cycle_adj)
            conception = payload.date + timedelta(days=payload.cycle_length - 14)
            gestational_days = (today - payload.date).days
        else:
            # Conception date: Due date is conception + 266 days
            conception = payload.date
            edd = conception + timedelta(days=266)
            theoretical_lmp = conception - timedelta(days=14)
            gestational_days = (today - theoretical_lmp).days

        gestational_days = max(0, gestational_days)
        weeks = gestational_days // 7
        days = gestational_days % 7

        days_remaining = max(0, (edd - today).days)
        progress = min(100.0, round((gestational_days / 280.0) * 100.0, 1))

        if weeks < 14:
            trimester = 1
        elif weeks < 28:
            trimester = 2
        else:
            trimester = 3

        # Key Milestones
        lmp_ref = edd - timedelta(days=280)
        milestones = [
            DueDateMilestone(
                milestone="First Heartbeat Audible via Sonogram",
                date=lmp_ref + timedelta(days=6 * 7),
                gestational_age="6 Weeks",
                description="Baby's cardiac tube begins rhythmic electrical contractions.",
            ),
            DueDateMilestone(
                milestone="End of First Trimester",
                date=lmp_ref + timedelta(days=13 * 7),
                gestational_age="13 Weeks",
                description="Miscarriage risk drops steeply; placenta takes over hormone synthesis.",
            ),
            DueDateMilestone(
                milestone="Anatomy Scan (Mid-Pregnancy Ultrasound)",
                date=lmp_ref + timedelta(days=20 * 7),
                gestational_age="20 Weeks",
                description="Comprehensive evaluation of fetal anatomy, heart chambers, and growth.",
            ),
            DueDateMilestone(
                milestone="Fetal Viability Milestone",
                date=lmp_ref + timedelta(days=24 * 7),
                gestational_age="24 Weeks",
                description="Crucial developmental threshold where survival with neonatal care rises sharply.",
            ),
            DueDateMilestone(
                milestone="Full Term Window",
                date=lmp_ref + timedelta(days=37 * 7),
                gestational_age="37 - 40 Weeks",
                description="Baby is fully matured and ready for labor and birth.",
            ),
        ]

        clinical = (
            f"Your Estimated Due Date (EDD) is {edd.strftime('%B %d, %Y')}. Only about 4-5% of babies arrive "
            f"on their exact due date; giving birth anywhere between 37 and 42 weeks is medically standard and healthy."
        )

        return DueDateResponse(
            estimated_due_date=edd,
            conception_date=conception,
            gestational_age_weeks=weeks,
            gestational_age_days=days,
            current_trimester=trimester,
            days_remaining=days_remaining,
            percentage_progress=progress,
            milestones=milestones,
            clinical_guideline=clinical,
        )

    # 9. IVF Due Date Calculator
    @staticmethod
    def calculate_ivf_due_date(payload: IvfDueDateRequest) -> IvfDueDateResponse:
        today = date.today()

        # Flo Health logic from decompiled bundle:
        # case "tr-1": r = 263 days; offset = 17 days (Day 3 embryo transfer)
        # case "tr-2": r = 261 days; offset = 19 days (Day 5 blastocyst transfer)
        # case "tr-3": r = 266 days; offset = 14 days (Egg retrieval / IUI / Day 0)
        # case "tr-4": r = 260 days; offset = 20 days (Day 6 blastocyst transfer)
        if payload.transfer_type == IvfTransferType.DAY_3:
            add_days = 263
            offset = 17
            label = "Day 3 Embryo Transfer"
        elif payload.transfer_type == IvfTransferType.DAY_5:
            add_days = 261
            offset = 19
            label = "Day 5 Blastocyst Transfer"
        elif payload.transfer_type == IvfTransferType.DAY_6:
            add_days = 260
            offset = 20
            label = "Day 6 Blastocyst Transfer"
        else:
            add_days = 266
            offset = 14
            label = "Egg Retrieval / Day 0 Fertilization"

        edd = payload.date + timedelta(days=add_days)
        theoretical_lmp = payload.date - timedelta(days=offset)

        gestational_days = max(0, (today - theoretical_lmp).days)
        weeks = gestational_days // 7
        days = gestational_days % 7
        days_rem = max(0, (edd - today).days)

        milestones = [
            DueDateMilestone(
                milestone="Beta hCG Blood Confirmation Test",
                date=payload.date + timedelta(days=10 if payload.transfer_type == IvfTransferType.DAY_5 else 14),
                gestational_age="~4 Weeks",
                description="First quantitative serum hCG test to confirm implantation.",
            ),
            DueDateMilestone(
                milestone="First Viability Ultrasound (Gestational Sac & Heartbeat)",
                date=theoretical_lmp + timedelta(days=45),
                gestational_age="6.5 Weeks",
                description="Confirmed intrauterine pregnancy and embryonic cardiac activity.",
            ),
            DueDateMilestone(
                milestone="Graduation from Fertility Clinic to OB/GYN",
                date=theoretical_lmp + timedelta(days=70),
                gestational_age="10 Weeks",
                description="Discontinuation of supplemental progesterone/estrogen as placenta takes over.",
            ),
            DueDateMilestone(
                milestone="Anatomy Scan",
                date=theoretical_lmp + timedelta(days=140),
                gestational_age="20 Weeks",
                description="Mid-pregnancy anatomical survey.",
            ),
        ]

        explanation = (
            f"Because the exact fertilization and transfer timing is known in Assisted Reproductive Technology (ART), "
            f"IVF due dates are among the most precise in obstetrics. For a {label}, "
            f"your estimated due date is {edd.strftime('%B %d, %Y')}."
        )

        return IvfDueDateResponse(
            estimated_due_date=edd,
            theoretical_lmp=theoretical_lmp,
            gestational_age_weeks=weeks,
            gestational_age_days=days,
            days_remaining=days_rem,
            transfer_type_label=label,
            milestones=milestones,
            clinical_explanation=explanation,
        )

    # 10. Due Date by Ultrasound
    @staticmethod
    def calculate_ultrasound_due_date(payload: UltrasoundDueDateRequest) -> UltrasoundDueDateResponse:
        today = date.today()

        # Flo Health logic from decompiled bundle:
        # scan_days = 7 * weeks + days
        # conception_date = ultrasound_date - scan_days + 14 (or theoretical LMP = scan_date - scan_days)
        # edd = ultrasound_date + (280 - scan_days)
        # current_days = scan_days + (today - ultrasound_date)
        scan_days = payload.weeks * 7 + payload.days
        edd = payload.ultrasound_date + timedelta(days=280 - scan_days)
        theoretical_lmp = payload.ultrasound_date - timedelta(days=scan_days)
        conception_date = theoretical_lmp + timedelta(days=14)

        days_since_scan = (today - payload.ultrasound_date).days
        current_total_days = max(0, scan_days + days_since_scan)
        current_weeks = current_total_days // 7
        current_days = current_total_days % 7

        days_remaining = max(0, (edd - today).days)

        acog = (
            "According to the American College of Obstetricians and Gynecologists (ACOG Committee Opinion No. 700), "
            "if ultrasound gestational age differs from LMP dating by more than 5 days in early first trimester (<= 8 6/7 weeks), "
            "or more than 7 days up to 13 6/7 weeks, the ultrasound dating should supersede the LMP due date."
        )

        insights = (
            f"Based on your scan on {payload.ultrasound_date.strftime('%B %d, %Y')} measuring {payload.weeks} weeks "
            f"{payload.days} days, your baby is currently at {current_weeks} weeks {current_days} days gestational age. "
            f"Estimated Delivery Date: {edd.strftime('%B %d, %Y')}."
        )

        return UltrasoundDueDateResponse(
            estimated_due_date=edd,
            estimated_conception_date=conception_date,
            gestational_age_at_scan_days=scan_days,
            current_gestational_age_weeks=current_weeks,
            current_gestational_age_days=current_days,
            days_remaining=days_remaining,
            acog_redating_criteria=acog,
            scan_insights=insights,
        )
