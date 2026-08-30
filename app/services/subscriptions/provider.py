from typing import Protocol, Any, Dict

class PaymentProvider(Protocol):
    def create_checkout(self, user_id: str, plan_id: str, price: float, currency: str) -> str:
        """Creates a checkout session and returns a checkout URL."""
        ...

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Verifies the webhook signature and returns the parsed payload."""
        ...

    def cancel_subscription(self, provider_subscription_id: str) -> bool:
        """Cancels a subscription with the provider."""
        ...
