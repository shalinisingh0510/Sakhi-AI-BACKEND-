from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Fallback objects if prometheus packages are not installed
try:
    from prometheus_client import Counter, Gauge
    sakhi_active_chat_streams = Gauge(
        "sakhi_active_chat_streams", "Number of currently active SSE chat streams"
    )
    sakhi_safety_guardrails_triggered_total = Counter(
        "sakhi_safety_guardrails_triggered_total", "Total number of safety emergencies triggered"
    )
except ImportError:
    class _DummyMetric:
        def inc(self, amount: float = 1) -> None:
            pass
        def dec(self, amount: float = 1) -> None:
            pass
        def set(self, value: float) -> None:
            pass
    sakhi_active_chat_streams = _DummyMetric()
    sakhi_safety_guardrails_triggered_total = _DummyMetric()


def setup_telemetry(app) -> None:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_group_untemplated=False,
            should_round_latency_decimals=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=[".*admin.*", "/metrics"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="inprogress",
            inprogress_labels=True,
        )
        instrumentator.instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        logger.info("prometheus-fastapi-instrumentator not installed. Telemetry endpoint not exposed.")
