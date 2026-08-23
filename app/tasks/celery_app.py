"""Celery application for Sakhi AI background tasks.

Configuration is read from environment variables via the application's
``Settings`` class.  The Celery app auto-discovers task modules inside
``app.tasks``.

Usage — start worker::

    celery -A app.tasks.celery_app worker --loglevel=info

Usage — development (eager mode, no broker needed)::

    Set ``SAKHI_CELERY_ALWAYS_EAGER=true`` in .env
"""

from __future__ import annotations

import os

from celery import Celery

# ---------------------------------------------------------------------------
# Read broker / result backend from environment.
# Defaults are suitable for local development (Redis on localhost).
# ---------------------------------------------------------------------------

_broker_url = os.environ.get("SAKHI_CELERY_BROKER_URL", "redis://localhost:6379/1")
_result_backend = os.environ.get("SAKHI_CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
_always_eager = os.environ.get("SAKHI_CELERY_ALWAYS_EAGER", "false").strip().lower() == "true"

celery_app = Celery(
    "sakhi",
    broker=_broker_url,
    backend=_result_backend,
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Development convenience — execute tasks synchronously.
    task_always_eager=_always_eager,
    task_eager_propagates=True,

    # Auto-discover task modules.
    include=["app.tasks.health_tasks"],
)
