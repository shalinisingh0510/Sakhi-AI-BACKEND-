from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.health_profile import HealthProfile
from app.models.symptom_log import SymptomLog
from app.models.energy_log import EnergyLog
from app.services.intelligence.insight_priority import PrioritizedInsight, InsightPriority, InsightPriorityEngine

class PersonalizationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.priority_engine = InsightPriorityEngine(db)

    def generate_weekly_insights(self, user_id: str) -> List[PrioritizedInsight]:
        """
        Analyzes the last 7 days of longitudinal data and returns prioritized insights.
        """
        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        if not profile:
            return []

        insights = []
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        # 1. Symptom Analysis
        recent_symptoms = self.db.query(SymptomLog).filter(
            SymptomLog.health_profile_id == profile.id,
            SymptomLog.start_date >= start_date
        ).all()
        
        severe_symptoms = [s for s in recent_symptoms if s.severity in ("severe", "worst")]
        if severe_symptoms:
            insights.append(PrioritizedInsight(
                message="You've logged severe symptoms recently. If they persist, consider discussing them with a healthcare professional.",
                priority=InsightPriority.SAFETY_RELEVANT,
                action_link="/health/symptoms"
            ))

        # 2. Energy Analysis
        recent_energy = self.db.query(EnergyLog).filter(
            EnergyLog.health_profile_id == profile.id,
            EnergyLog.log_date >= start_date
        ).all()
        
        low_energy_days = sum(1 for e in recent_energy if getattr(e, 'energy_level', 0) <= 2)
        if low_energy_days >= 3:
            insights.append(PrioritizedInsight(
                message="You've been logging lower energy more often over the past week. Would you like to review your activity and nutrition?",
                priority=InsightPriority.IMPORTANT,
                action_link="/health/energy"
            ))
        elif len(recent_energy) >= 5:
            insights.append(PrioritizedInsight(
                message="Great job logging your energy consistently this week!",
                priority=InsightPriority.INFO
            ))

        # 3. Filter through priority engine
        final_insights = self.priority_engine.filter_and_prioritize(insights)
        return final_insights
