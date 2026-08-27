from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.services.auth import StoredUser
from app.models.wellness_plan import WellnessPlan, PlanStatus
from app.services.wellness_planning.generator import WellnessPlanGenerator

router = APIRouter(prefix="/wellness/plans", tags=["wellness-plans"])

class WellnessPlanResponse(BaseModel):
    id: str
    title: str
    action_type: str
    frequency: str
    status: str
    reasoning: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class WellnessPlanUpdateRequest(BaseModel):
    status: str

@router.get("", response_model=List[WellnessPlanResponse])
def get_wellness_plans(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve current wellness plans for the user.
    """
    plans = db.query(WellnessPlan).filter(
        WellnessPlan.user_id == current_user.id,
        WellnessPlan.status.in_([PlanStatus.SUGGESTED, PlanStatus.ACCEPTED])
    ).all()
    
    return plans

@router.post("/generate", response_model=List[WellnessPlanResponse])
def generate_plans(
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger manual generation of daily plans.
    """
    generator = WellnessPlanGenerator(db)
    new_plans = generator.generate_daily_plans(current_user.id)
    return new_plans

@router.patch("/{plan_id}", response_model=WellnessPlanResponse)
def update_plan_status(
    plan_id: str,
    payload: WellnessPlanUpdateRequest,
    current_user: StoredUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the status of a wellness plan (e.g., ACCEPTED, COMPLETED, SKIPPED).
    """
    plan = db.query(WellnessPlan).filter(
        WellnessPlan.id == plan_id,
        WellnessPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    try:
        new_status = PlanStatus(payload.status.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    plan.status = new_status
    if new_status == PlanStatus.COMPLETED:
        plan.completed_at = datetime.utcnow()
        
    db.commit()
    db.refresh(plan)
    return plan
