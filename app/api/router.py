from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.lessons import router as lessons_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.progress import router as progress_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(conversations_router, prefix="/api/v1")
api_router.include_router(lessons_router, prefix="/api/v1")
api_router.include_router(progress_router, prefix="/api/v1")
api_router.include_router(notifications_router, prefix="/api/v1")
api_router.include_router(analytics_router, prefix="/api/v1")
api_router.include_router(admin_router, prefix="/api/v1")
