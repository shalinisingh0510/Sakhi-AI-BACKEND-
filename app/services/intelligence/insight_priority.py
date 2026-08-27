import enum
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.health_profile import HealthProfile
from app.models.symptom_log import SymptomLog
from app.models.energy_log import EnergyLog
from app.models.activity import ActivityLog

class InsightPriority(str, enum.Enum):
    INFO = "INFO"
    USEFUL = "USEFUL"
    IMPORTANT = "IMPORTANT"
    SAFETY_RELEVANT = "SAFETY_RELEVANT"

class PrioritizedInsight:
    def __init__(self, message: str, priority: InsightPriority, action_link: Optional[str] = None):
        self.message = message
        self.priority = priority
        self.action_link = action_link

class InsightPriorityEngine:
    """
    Evaluates raw signals and decides if they should be shown to the user.
    Prevents notification fatigue by dropping low-value repeated insights.
    """
    def __init__(self, db: Session):
        self.db = db
        
    def filter_and_prioritize(self, insights: List[PrioritizedInsight]) -> List[PrioritizedInsight]:
        """
        Filters and sorts insights to return only top 3 relevant messages.
        """
        if not insights:
            return []
            
        # Priority mapping
        p_map = {
            InsightPriority.SAFETY_RELEVANT: 4,
            InsightPriority.IMPORTANT: 3,
            InsightPriority.USEFUL: 2,
            InsightPriority.INFO: 1
        }
        
        # Sort by priority
        insights.sort(key=lambda x: p_map[x.priority], reverse=True)
        
        # Return top 3, but drop INFO if we have higher priorities
        final_list = []
        for insight in insights[:3]:
            if insight.priority == InsightPriority.INFO and any(x.priority != InsightPriority.INFO for x in final_list):
                continue
            final_list.append(insight)
            
        return final_list
