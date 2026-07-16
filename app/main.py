from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db import SQLiteAuthStore
from app.services.auth import AuthService, AuthStoreProtocol

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
