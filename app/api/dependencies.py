from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.services.ai import AIService
from app.services.analytics import AnalyticsService
from app.services.auth import AuthService, InvalidTokenError, StoredUser
from app.services.lessons import LessonService
from app.services.notifications import NotificationService
from app.services.progress import ProgressService


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def get_lesson_service(request: Request) -> LessonService:
    return request.app.state.lesson_service


def get_notification_service(request: Request) -> NotificationService:
    return request.app.state.notification_service


def get_progress_service(request: Request) -> ProgressService:
    return request.app.state.progress_service


def get_analytics_service(request: Request) -> AnalyticsService:
    return request.app.state.analytics_service


def get_current_user(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> StoredUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use the Bearer scheme.",
        )

    try:
        return auth_service.resolve_current_user(access_token=token.strip())
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_roles(*roles: str):
    allowed_roles = {role.strip().lower() for role in roles if role.strip()}

    def dependency(current_user: StoredUser = Depends(get_current_user)) -> StoredUser:
        if current_user.role.lower() not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return dependency
