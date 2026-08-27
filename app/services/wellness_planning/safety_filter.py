import enum
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy.orm import Session

class DietRestriction(str, enum.Enum):
    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    NONE = "NONE"

class SafetyFilterService:
    """
    Enforces age policies and dietary restrictions for wellness plans.
    """
    def __init__(self, db: Session):
        self.db = db

    def filter_nutrition_action(self, action_title: str, user_age: int, diet: DietRestriction) -> Optional[str]:
        """
        Validates a nutrition action against safety rules. Returns safe title or None if rejected.
        """
        title_lower = action_title.lower()
        
        # 1. Age Policy (14-17)
        if 13 <= user_age < 18:
            unsafe_keywords = ["fasting", "deficit", "lose weight", "restrict", "skip meal"]
            if any(w in title_lower for w in unsafe_keywords):
                return None  # Block
                
        # 2. Dietary Filter
        if diet == DietRestriction.VEGETARIAN:
            meat_keywords = ["chicken", "beef", "pork", "fish", "meat"]
            if any(w in title_lower for w in meat_keywords):
                return None
                
        if diet == DietRestriction.VEGAN:
            animal_keywords = ["chicken", "beef", "pork", "fish", "meat", "egg", "dairy", "milk", "cheese", "honey"]
            if any(w in title_lower for w in animal_keywords):
                return None
                
        return action_title

    def filter_activity_action(self, action_title: str, user_age: int) -> Optional[str]:
        """
        Validates activity actions.
        """
        title_lower = action_title.lower()
        if 13 <= user_age < 18:
            unsafe_keywords = ["burn calories", "fat burning", "extreme"]
            if any(w in title_lower for w in unsafe_keywords):
                return None
                
        return action_title
