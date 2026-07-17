from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_notification_service, pagination_params
from app.schemas.notification import NotificationItem, UnreadCountResponse
from app.services.auth import StoredUser
from app.services.notifications import NotificationNotFoundError, NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationItem])
def list_notifications(
    pagination: tuple[int, int] = Depends(pagination_params),
    current_user: StoredUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationItem]:
    offset, limit = pagination
    all_notifications = notification_service.list_notifications(user_id=current_user.id)
    return all_notifications[offset : offset + limit]


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    current_user: StoredUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    return UnreadCountResponse(unread_count=notification_service.count_unread(user_id=current_user.id))


@router.patch("/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(
    notification_id: str,
    current_user: StoredUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationItem:
    try:
        return notification_service.mark_as_read(notification_id=notification_id, user_id=current_user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
