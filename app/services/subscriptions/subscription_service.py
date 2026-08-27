from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.subscription import SubscriptionPlan, UserSubscription
from app.services.subscriptions.provider import PaymentProvider

class SubscriptionNotFoundError(Exception):
    pass

class PlanNotFoundError(Exception):
    pass

class SubscriptionService:
    def __init__(self, db: Session, provider: PaymentProvider):
        self.db = db
        self.provider = provider

    def list_plans(self) -> List[SubscriptionPlan]:
        return self.db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)).all()

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        return self.db.scalars(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()

    def create_checkout(self, user_id: str, plan_id: str) -> str:
        plan = self.db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)).first()
        if not plan:
            raise PlanNotFoundError("Plan not found")
        
        return self.provider.create_checkout(user_id, plan.id, plan.price, plan.currency)

    def handle_webhook(self, payload: bytes, signature: str):
        event = self.provider.verify_webhook(payload, signature)
        
        event_type = event.get("type")
        data = event.get("data", {})
        
        if event_type == "subscription.created" or event_type == "subscription.updated":
            user_id = data.get("user_id")
            plan_id = data.get("plan_id")
            status = data.get("status", "active")
            provider_sub_id = data.get("provider_subscription_id")
            
            # Upsert user subscription
            sub = self.get_user_subscription(user_id)
            if not sub:
                sub = UserSubscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status=status,
                    provider="mock",
                    provider_subscription_id=provider_sub_id,
                    current_period_end=datetime.now(timezone.utc) + timedelta(days=30)
                )
                self.db.add(sub)
            else:
                sub.plan_id = plan_id
                sub.status = status
                sub.provider_subscription_id = provider_sub_id
            self.db.commit()

        elif event_type == "subscription.canceled":
            user_id = data.get("user_id")
            sub = self.get_user_subscription(user_id)
            if sub:
                sub.status = "canceled"
                sub.canceled_at = datetime.now(timezone.utc)
                self.db.commit()
    
    def cancel_subscription(self, user_id: str) -> UserSubscription:
        sub = self.get_user_subscription(user_id)
        if not sub:
            raise SubscriptionNotFoundError("No active subscription")
        
        if sub.provider_subscription_id:
            self.provider.cancel_subscription(sub.provider_subscription_id)
        
        sub.status = "canceled"
        sub.canceled_at = datetime.now(timezone.utc)
        self.db.commit()
        return sub
