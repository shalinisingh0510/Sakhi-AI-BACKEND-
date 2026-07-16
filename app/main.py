from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db import SQLiteAuthStore, SQLiteConversationStore, SQLiteLessonStore, SQLiteNotificationStore, SQLiteProgressStore
from app.services.ai import AIService
from app.services.auth import AuthService, AuthStoreProtocol
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
    app.state.auth_service = AuthService(settings, store=app.state.auth_store)
    app.state.ai_store = SQLiteConversationStore(settings.database_path)
    app.state.ai_service = AIService(settings, store=app.state.ai_store)
    app.state.lesson_store = SQLiteLessonStore(settings.database_path)
    app.state.lesson_service = LessonService(settings, store=app.state.lesson_store)
    app.state.notification_store = SQLiteNotificationStore(settings.database_path)
    app.state.notification_service = NotificationService(settings, store=app.state.notification_store)
    app.state.progress_store = SQLiteProgressStore(settings.database_path)
    app.state.progress_service = ProgressService(
        settings,
        store=app.state.progress_store,
        lesson_service=app.state.lesson_service,
        notification_service=app.state.notification_service,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "message": "Sakhi AI API is running",
            "status": "ok",
        }

    return app


app = create_app()
