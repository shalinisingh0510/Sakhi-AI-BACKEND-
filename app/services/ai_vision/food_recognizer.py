from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.nutrition import Food
from app.services.ai_vision.provider import get_vision_provider, FoodCandidate

class RecognizedFood(FoodCandidate):
    """
    Extends FoodCandidate with the canonical database ID if matched.
    """
    canonical_food_id: str | None = None
    warning: str | None = None

class FoodRecognitionService:
    def __init__(self, db: Session):
        self.db = db
        self.vision_provider = get_vision_provider()

    def analyze_food_image(self, image_bytes: bytes) -> List[RecognizedFood]:
        """
        Processes an image, extracts candidates, and attempts to map them 
        to the internal Food database.
        """
        # 1. Image validation (size/format) is typically handled at the endpoint layer.
        
        # 2. Get candidates from Vision AI
        candidates = self.vision_provider.identify_food(image_bytes)
        
        # 3. Map to canonical food database
        recognized_results = []
        for c in candidates:
            # Simple keyword matching (in production, use pg_trgm or semantic search)
            stmt = select(Food).filter(Food.name.ilike(f"%{c.name}%")).limit(1)
            matched_food = self.db.execute(stmt).scalar_one_or_none()
            
            rec = RecognizedFood(
                name=c.name,
                estimated_quantity=c.estimated_quantity,
                confidence=c.confidence
            )
            
            if matched_food:
                rec.canonical_food_id = matched_food.id
                # Ensure the name displayed is our canonical name for consistency
                rec.name = matched_food.name 
            else:
                rec.warning = "Food not found in database. Manual entry required."
                
            if c.confidence == "LOW":
                rec.warning = "Low confidence detection. Please verify."
                
            recognized_results.append(rec)
            
        return recognized_results
