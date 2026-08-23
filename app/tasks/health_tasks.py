"""Health-related background tasks — placeholders for Phase 1+.

Phase 0 provides only a ``ping`` test task to verify that the Celery
infrastructure works end-to-end.  Actual health tasks will be added
in future phases.

Future tasks:
- ``generate_daily_wellness_summary``
- ``generate_weekly_summary``
- ``generate_monthly_summary``
- ``generate_ai_insight``
- ``sync_wearable_data``
- ``run_rag_ingestion``
- ``schedule_health_notification``
"""

from __future__ import annotations

from app.tasks.celery_app import celery_app


@celery_app.task(name="sakhi.health.ping")
def ping() -> dict[str, str]:
    """Simple connectivity test — returns a static response.

    Useful for verifying broker connectivity and task routing.

    Example::

        from app.tasks.health_tasks import ping
        result = ping.delay()
        print(result.get(timeout=5))
    """
    return {"status": "pong", "source": "sakhi.health.ping"}
