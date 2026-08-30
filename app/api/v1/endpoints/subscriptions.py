from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.subscription import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionPlanResponse,
    UserSubscriptionResponse,
)
from app.services.auth import StoredUser
from app.services.subscriptions.mock_provider import MockPaymentProvider
from app.services.subscriptions.subscription_service import PlanNotFoundError, SubscriptionNotFoundError, SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    provider = MockPaymentProvider()
    return SubscriptionService(db, provider)


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
def get_plans(service: SubscriptionService = Depends(get_subscription_service)):
    """List available subscription plans."""
    return service.list_plans()


@router.get("/me", response_model=UserSubscriptionResponse)
def get_my_subscription(
    current_user: StoredUser = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """Get the current user's subscription."""
    sub = service.get_user_subscription(current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    current_user: StoredUser = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """Create a checkout session for a plan."""
    try:
        url = service.create_checkout(current_user.id, request.plan_id)
        return CheckoutResponse(checkout_url=url, transaction_id="mock_tx")
    except PlanNotFoundError:
        raise HTTPException(status_code=404, detail="Plan not found")


@router.post("/cancel", response_model=UserSubscriptionResponse)
def cancel_subscription(
    current_user: StoredUser = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """Cancel the current subscription."""
    try:
        return service.cancel_subscription(current_user.id)
    except SubscriptionNotFoundError:
        raise HTTPException(status_code=404, detail="No active subscription found")


@router.post("/webhook")
async def webhook_handler(
    request: Request,
    service: SubscriptionService = Depends(get_subscription_service),
):
    """Handle incoming webhooks from the payment provider."""
    # In a real scenario, we'd verify the signature header
    payload = await request.body()
    signature = request.headers.get("x-mock-signature", "mock")
    
    try:
        service.handle_webhook(payload, signature)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
