from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.api.v1.endpoints.feedback import router as feedback_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.health_profile import router as health_profile_router
from app.api.v1.endpoints.lessons import router as lessons_router
from app.api.v1.endpoints.media import router as media_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.openapi import router as openapi_router
from app.api.v1.endpoints.recommendations import router as recommendations_router
from app.api.v1.endpoints.progress import router as progress_router
from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.endpoints.cycles import router as cycles_router
from app.api.v1.endpoints.wellness import router as wellness_router
from app.api.v1.endpoints.nutrition import router as nutrition_router

api_router = APIRouter()
api_router.include_router(nutrition_router, prefix="/api/v1")
api_router.include_router(wellness_router, prefix="/api/v1")
api_router.include_router(cycles_router, prefix="/api/v1")
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(health_profile_router, prefix="/api/v1")
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(conversations_router, prefix="/api/v1")
api_router.include_router(lessons_router, prefix="/api/v1")
api_router.include_router(feedback_router, prefix="/api/v1")
api_router.include_router(openapi_router, prefix="/api/v1")
api_router.include_router(recommendations_router, prefix="/api/v1")
api_router.include_router(progress_router, prefix="/api/v1")
api_router.include_router(notifications_router, prefix="/api/v1")
api_router.include_router(analytics_router, prefix="/api/v1")
api_router.include_router(admin_router, prefix="/api/v1")
api_router.include_router(media_router, prefix="/api/v1")
api_router.include_router(ws_router, prefix="/api/v1")
