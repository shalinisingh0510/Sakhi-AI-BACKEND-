import uuid
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.wellness_plan import WellnessGoal, WellnessPlan, PlanStatus, PlanFrequency
from app.services.wellness_planning.safety_filter import SafetyFilterService, DietRestriction
from app.models.health_profile import HealthProfile

class WellnessPlanGenerator:
    def __init__(self, db: Session):
        self.db = db
        self.safety_filter = SafetyFilterService(db)

    def generate_daily_plans(self, user_id: str) -> List[WellnessPlan]:
        """
        Generates 1-3 actionable plans based on user's active goals and longitudinal insights.
        """
        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        user_age = 25
        if profile and profile.date_of_birth:
            today = datetime.date.today()
            user_age = today.year - profile.date_of_birth.year - ((today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day))
            
        diet = DietRestriction.NONE
        if profile and profile.dietary_preference:
            if "VEGAN" in profile.dietary_preference.upper():
                diet = DietRestriction.VEGAN
            elif "VEGETARIAN" in profile.dietary_preference.upper():
                diet = DietRestriction.VEGETARIAN

        goals = self.db.query(WellnessGoal).filter(
            WellnessGoal.user_id == user_id, 
            WellnessGoal.active == True
        ).order_by(WellnessGoal.priority.desc()).limit(3).all()

        generated_plans = []
        
        for goal in goals:
            action_title = ""
            action_type = ""
            reasoning = ""
            
            if goal.goal_type == "BETTER_NUTRITION":
                action_title = "Add a protein-rich food to your lunch"
                action_type = "LOG_NUTRITION"
                reasoning = "Based on your goal to improve nutrition consistency."
                
                # Apply safety filter
                action_title = self.safety_filter.filter_nutrition_action(action_title, user_age, diet)
                
            elif goal.goal_type == "CONSISTENT_ACTIVITY":
                action_title = "Take a 20-minute walk"
                action_type = "LOG_ACTIVITY"
                reasoning = "You missed activity tracking for the last 2 days."
                
                action_title = self.safety_filter.filter_activity_action(action_title, user_age)
                
            elif goal.goal_type == "BETTER_HYDRATION":
                action_title = "Drink an extra glass of water this morning"
                action_type = "LOG_WATER"
                reasoning = "General wellness goal."

            if action_title:
                plan = WellnessPlan(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    goal_id=goal.id,
                    title=action_title,
                    action_type=action_type,
                    frequency=PlanFrequency.DAILY,
                    status=PlanStatus.SUGGESTED,
                    reasoning=reasoning
                )
                self.db.add(plan)
                generated_plans.append(plan)

        self.db.commit()
        for p in generated_plans:
            self.db.refresh(p)
            
        return generated_plans
