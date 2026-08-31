from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import ConnectionPool
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.router import api_router
from app.core.cache import build_cache_backend
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    access_log_middleware,
    configure_rate_limiter,
    global_exception_handler,
    rate_limit_middleware,
    request_size_middleware,
    security_headers_middleware,
)
from app.core.sentry import init_sentry
from app.core.telemetry import setup_telemetry
from app.core.token_blacklist import build_token_blacklist
from app.db import (
    PostgresAnalyticsStore,
    PostgresAuthStore,
    PostgresConversationStore,
    PostgresFeedbackStore,
    PostgresLessonStore,
    PostgresMediaStore,
    PostgresNotificationStore,
    PostgresProgressStore,
)
from app.db.session import init_db
from app.services.ai import AIService
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, AuthStoreProtocol
from app.services.chat import ChatService
from app.services.email import EmailService, build_email_backend
from app.services.feedback import FeedbackService
from app.services.lessons import LessonService
from app.services.media import MediaService
from app.services.notifications import NotificationService
from app.services.progress import ProgressService
from app.services.recommendations import RecommendationService
from app.services.storage import CloudflareStorageService

configure_logging()
startup_logger = logging.getLogger('sakhi.startup')


def create_app(
    settings: Settings | None = None,
    auth_store: AuthStoreProtocol | None = None,
) -> FastAPI:
    try:
        settings = settings or get_settings()
        init_sentry(settings)

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            if hasattr(app.state, 'db_pool'):
                app.state.db_pool.close()

        openapi_tags = [
            {"name": "Authentication", "description": "Operations with users and JWT authentication."},
            {"name": "Chat", "description": "Endpoints for real-time multilingual AI chat."},
            {"name": "Learning Modules", "description": "Endpoints to fetch educational content and track progress."},
            {"name": "Admin", "description": "Administrative endpoints for metrics and content management."},
            {"name": "Health", "description": "System health and readiness probes."},
        ]

        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            debug=settings.debug,
            lifespan=lifespan,
            openapi_tags=openapi_tags,
        )

        db_pool = ConnectionPool(
            settings.database_url,
            kwargs={"connect_timeout": 10, "autocommit": True},
            check=ConnectionPool.check_connection,
        )
        app.state.db_pool = db_pool

        # Initialise SQLAlchemy engine (used by health domain and future ORM-backed services).
        init_db(settings.database_url)

        app.state.settings = settings
        app.state.auth_store = auth_store or PostgresAuthStore(db_pool)

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
        app.state.ai_store = PostgresConversationStore(db_pool)
        app.state.ai_service = AIService(settings, store=app.state.ai_store)
        app.state.chat_service = ChatService(settings, store=app.state.ai_store)
        app.state.lesson_store = PostgresLessonStore(db_pool)
        app.state.lesson_service = LessonService(settings, store=app.state.lesson_store, cache=cache_backend)
        app.state.feedback_store = PostgresFeedbackStore(db_pool)
        app.state.feedback_service = FeedbackService(settings, store=app.state.feedback_store)

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

        app.state.notification_store = PostgresNotificationStore(db_pool)
        app.state.notification_service = NotificationService(
            settings,
            store=app.state.notification_store,
            auth_store=app.state.auth_store,
            email_service=app.state.email_service,
        )
        app.state.progress_store = PostgresProgressStore(db_pool)
        app.state.progress_service = ProgressService(
            settings,
            store=app.state.progress_store,
            lesson_service=app.state.lesson_service,
            notification_service=app.state.notification_service,
        )
        app.state.analytics_store = PostgresAnalyticsStore(db_pool)
        app.state.analytics_service = AnalyticsService(settings, store=app.state.analytics_store, cache=cache_backend)
        app.state.recommendation_service = RecommendationService(
            lesson_service=app.state.lesson_service,
            progress_service=app.state.progress_service,
            analytics_service=app.state.analytics_service,
        )

        # Media and Storage services
        app.state.storage_service = CloudflareStorageService(settings)
        app.state.media_store = PostgresMediaStore(db_pool)
        app.state.media_service = MediaService(
            settings,
            store=app.state.media_store,
            storage_service=app.state.storage_service,
        )

        configure_rate_limiter(settings.rate_limit_requests_per_minute)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Conversation-Id", "X-Response-Time"],
        )
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

        app.middleware("http")(security_headers_middleware)
        app.middleware("http")(request_size_middleware)
        app.middleware("http")(rate_limit_middleware)
        app.middleware("http")(access_log_middleware)
        app.middleware("http")(global_exception_handler)

        app.include_router(api_router)

        @app.get('/api/health', include_in_schema=False)
        def lightweight_health_check() -> dict[str, str]:
            return {'status': 'ok'}

        @app.get('/', include_in_schema=False)
        def root() -> dict[str, str]:
            return {
                'message': 'Sakhi AI API is running',
                'status': 'ok',
            }

        setup_telemetry(app)

        return app
    except Exception as exc:
        startup_logger.exception('Failed to initialize Sakhi AI backend services.')
        raise RuntimeError('Sakhi AI backend failed to start during initialization.') from exc


app = create_app()
