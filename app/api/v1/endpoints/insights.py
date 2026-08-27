from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.services.auth import StoredUser
from app.services.intelligence.personalization import PersonalizationEngine

router = APIRouter(prefix="/insights", tags=["insights"])

class InsightResponse(BaseModel):
    message: str
    priority: str
    action_link: Optional[str] = None

@router.get("/weekly", response_model=List[InsightResponse])
def get_weekly_insights(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns prioritized weekly insights based on the user's longitudinal health tracking.
    """
    engine = PersonalizationEngine(db)
    try:
        insights = engine.generate_weekly_insights(current_user.id)
        return [
            InsightResponse(
                message=i.message,
                priority=i.priority,
                action_link=i.action_link
            ) for i in insights
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
