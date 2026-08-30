from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional

class SubscriptionPlanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    currency: str
    interval: str
    features: List[str]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class CheckoutRequest(BaseModel):
    plan_id: str

class CheckoutResponse(BaseModel):
    checkout_url: str
    transaction_id: str

class UserSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str
    provider: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool

    model_config = ConfigDict(from_attributes=True)
