from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.services.auth import StoredUser
from app.services.ai_vision.food_recognizer import FoodRecognitionService

router = APIRouter(prefix="/food-vision", tags=["food-vision"])

class FoodDetectionResponse(BaseModel):
    name: str
    estimated_quantity: str
    confidence: str
    canonical_food_id: Optional[str] = None
    warning: Optional[str] = None

@router.post("/analyze", response_model=List[FoodDetectionResponse])
async def analyze_food_image(
    file: UploadFile = File(...),
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes an uploaded image of food and returns mapped candidates.
    The image is processed in memory and immediately discarded to preserve privacy.
    """
    # Basic validation
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format. Use JPEG, PNG, or WEBP.")
        
    # Read to memory
    image_bytes = await file.read()
    
    if len(image_bytes) > 10 * 1024 * 1024: # 10MB limit
        raise HTTPException(status_code=400, detail="Image size exceeds 10MB limit.")
        
    # Send to recognition service
    service = FoodRecognitionService(db)
    
    try:
        results = service.analyze_food_image(image_bytes)
        # Note: image_bytes is dropped here, no permanent storage.
        return [
            FoodDetectionResponse(
                name=r.name,
                estimated_quantity=r.estimated_quantity,
                confidence=r.confidence,
                canonical_food_id=r.canonical_food_id,
                warning=r.warning
            ) for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
