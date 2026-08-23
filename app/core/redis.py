"""Unified Redis connection factory for Sakhi AI.

Provides a single shared Redis client that can be reused by any
subsystem (cache, token blacklist, rate limiter, Celery, health
state, etc.) to avoid creating duplicate connections.

Existing code in ``cache.py`` and ``token_blacklist.py`` currently
creates its own Redis instances.  This module offers a shared
alternative that new subsystems should prefer.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sakhi.redis")

_client: Any | None = None


def get_redis_client(
    *,
    redis_url: str = "redis://localhost:6379/0",
    decode_responses: bool = True,
) -> Any:
    """Return a shared Redis client, creating one on first call.

    Falls back gracefully if the ``redis`` package is not installed or
    the server is unreachable — returns ``None`` in that case so that
    callers can degrade to in-memory alternatives.
    """
    global _client  # noqa: PLW0603

    if _client is not None:
        return _client

    try:
        import redis as redis_module  # type: ignore[import-untyped]

        _client = redis_module.Redis.from_url(
            redis_url, decode_responses=decode_responses
        )
        _client.ping()
        logger.info("Redis connection established (%s).", redis_url.split("@")[-1])
        return _client
    except Exception as exc:
        logger.warning("Redis unavailable (%s). Features requiring Redis will degrade.", exc)
        return None


def close_redis_client() -> None:
    """Close the shared Redis connection (call during shutdown)."""
    global _client  # noqa: PLW0603
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
