from __future__ import annotations

import logging
from app.core.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    if settings.environment == "production" and settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                integrations=[
                    StarletteIntegration(transaction_style="endpoint"),
                    FastApiIntegration(transaction_style="endpoint"),
                ],
                traces_sample_rate=1.0,
            )
        except ImportError:
            logger.warning("sentry-sdk is not installed. Skipping sentry initialization.")
