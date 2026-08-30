import uuid
import json
from typing import Any, Dict
from app.services.subscriptions.provider import PaymentProvider

class MockPaymentProvider(PaymentProvider):
    def create_checkout(self, user_id: str, plan_id: str, price: float, currency: str) -> str:
        # Returns a mock URL that the frontend can pretend to navigate to
        transaction_id = str(uuid.uuid4())
        return f"https://mock-payment.sakhiai.local/checkout/{transaction_id}?plan={plan_id}"

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        # For mock, we'll just parse the payload assuming it's valid JSON
        try:
            return json.loads(payload.decode('utf-8'))
        except Exception as e:
            raise ValueError("Invalid mock webhook payload") from e

    def cancel_subscription(self, provider_subscription_id: str) -> bool:
        # Mock cancellation always succeeds
        return True
