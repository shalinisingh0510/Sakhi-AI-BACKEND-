from fastapi import Depends, Header, HTTPException, Query, Request, status

from app.services.ai import AIService
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, InvalidTokenError, StoredUser
from app.services.chat import ChatService
from app.services.feedback import FeedbackService
from app.services.lessons import LessonService
from app.services.notifications import NotificationService
from app.services.progress import ProgressService
from app.services.recommendations import RecommendationService
from app.db.dependencies import get_db


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_lesson_service(request: Request) -> LessonService:
    return request.app.state.lesson_service


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


def get_feedback_service(request: Request) -> FeedbackService:
    return request.app.state.feedback_service


def get_progress_service(request: Request) -> ProgressService:
    return request.app.state.progress_service


def get_recommendation_service(request: Request) -> RecommendationService:
    return request.app.state.recommendation_service


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_email_service(request: Request):
    return request.app.state.email_service


def get_current_user(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> StoredUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing authorization header.',
        )

    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization header must use the Bearer scheme.',
        )

    try:
        return auth_service.resolve_current_user(access_token=token.strip())
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> StoredUser | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return None

    try:
        return auth_service.resolve_current_user(access_token=token.strip())
    except InvalidTokenError:
        return None


def require_roles(*roles: str):
    allowed_roles = {role.strip().lower() for role in roles if role.strip()}

    def dependency(current_user: StoredUser = Depends(get_current_user)) -> StoredUser:
        if current_user.role.lower() not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You do not have permission to access this resource.',
            )
        return current_user

    return dependency


def pagination_params(
    page: int = Query(default=1, ge=1, description='Page number (1-indexed)'),
    page_size: int = Query(default=20, ge=1, le=100, description='Items per page'),
) -> tuple[int, int]:
    """Return (offset, limit) for use in list queries."""
    offset = (page - 1) * page_size
    return offset, page_size


def verify_profile_ownership(profile_id: str, current_user: StoredUser = Depends(get_current_user), db=Depends(get_db)):
    """
    Dependency to verify that the requested HealthProfile ID actually belongs to the current user.
    Prevents Insecure Direct Object Reference (IDOR) attacks.
    """
    from app.models.health_profile import HealthProfile

    # We could do a direct query here, but as a quick dependency we just check user ownership.
    # We use db.query instead of importing a service to avoid circular deps.
    profile = db.query(HealthProfile).filter(HealthProfile.id == profile_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail='Health profile not found')

    if profile.user_id != current_user.id:
        # Phase 16: Return 404 instead of 403 to prevent data existence leakage (enumeration)
        raise HTTPException(status_code=404, detail='Health profile not found')

    return profile
