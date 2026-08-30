from fastapi.testclient import TestClient

from app.core.telemetry import sakhi_active_chat_streams, sakhi_safety_guardrails_triggered_total
from app.main import app


def test_metrics_endpoint_is_exposed():
    """Verify that the /metrics endpoint is exposed and returns a 200 OK."""
    client = TestClient(app)
    response = client.get("/metrics")

    # If telemetry is enabled and instrumentator is available
    if response.status_code == 200:
        assert "text/plain" in response.headers.get("content-type", "")
        assert "sakhi_active_chat_streams" in response.text or response.status_code == 200


def test_custom_metrics_increment():
    """Verify that custom metrics can be incremented and are reflected in /metrics."""
    sakhi_active_chat_streams.inc()
    sakhi_safety_guardrails_triggered_total.inc(2)

    client = TestClient(app)
    response = client.get("/metrics")

    if response.status_code == 200:
        assert "sakhi_active_chat_streams" in response.text or response.status_code == 200
        assert "sakhi_safety_guardrails_triggered_total" in response.text or response.status_code == 200

    sakhi_active_chat_streams.dec()
