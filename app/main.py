from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.cache import build_cache_backend
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    access_log_middleware,
    configure_rate_limiter,
    rate_limit_middleware,
    request_size_middleware,
    security_headers_middleware,
)
from app.core.token_blacklist import build_token_blacklist
from app.db import SQLiteAuthStore, SQLiteAnalyticsStore, SQLiteConversationStore, SQLiteLessonStore, SQLiteNotificationStore, SQLiteProgressStore
from app.services.ai import AIService
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, AuthStoreProtocol
from app.services.email import EmailService, build_email_backend
from app.services.lessons import LessonService
from app.services.notifications import NotificationService
from app.services.progress import ProgressService

configure_logging()


def create_app(
    settings: Settings | None = None,
    auth_store: AuthStoreProtocol | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.state.settings = settings
    app.state.auth_store = auth_store or SQLiteAuthStore(settings.database_path)

    cache_backend = build_cache_backend(
        backend=settings.cache_backend,
        redis_url=settings.redis_url,
        redis_key_prefix=settings.redis_cache_prefix,
    )
    app.state.cache_backend = cache_backend

    token_blacklist = build_token_blacklist(
        backend=settings.token_blacklist_backend,
        redis_url=settings.redis_url,
        redis_key_prefix=settings.redis_token_blacklist_prefix,
    )
    app.state.token_blacklist = token_blacklist
    app.state.auth_service = AuthService(settings, store=app.state.auth_store, blacklist=token_blacklist)
    app.state.ai_store = SQLiteConversationStore(settings.database_path)
    app.state.ai_service = AIService(settings, store=app.state.ai_store)
    app.state.lesson_store = SQLiteLessonStore(settings.database_path)
    app.state.lesson_service = LessonService(settings, store=app.state.lesson_store, cache=cache_backend)

    # Email service
    email_backend = build_email_backend(
        settings.email_backend,
        host=settings.email_host,
        port=settings.email_port,
        username=settings.email_username,
        password=settings.email_password.get_secret_value(),
        sender=settings.email_from,
        use_tls=settings.email_use_tls,
    )
    app.state.email_service = EmailService(backend=email_backend)

    app.state.notification_store = SQLiteNotificationStore(settings.database_path)
    app.state.notification_service = NotificationService(
        settings,
        store=app.state.notification_store,
        auth_store=app.state.auth_store,
        email_service=app.state.email_service,
    )
    app.state.progress_store = SQLiteProgressStore(settings.database_path)
    app.state.progress_service = ProgressService(
        settings,
        store=app.state.progress_store,
        lesson_service=app.state.lesson_service,
        notification_service=app.state.notification_service,
    )
    app.state.analytics_store = SQLiteAnalyticsStore(settings.database_path)
    app.state.analytics_service = AnalyticsService(settings, store=app.state.analytics_store, cache=cache_backend)

    configure_rate_limiter(settings.rate_limit_requests_per_minute)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(request_size_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(access_log_middleware)

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "message": "Sakhi AI API is running",
            "status": "ok",
        }

    return app


app = create_app()
