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


@router.post("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    current_user: StoredUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> dict[str, int]:
    """Mark every unread notification as read. Returns the count of notifications updated."""
    updated = notification_service.mark_all_as_read(user_id=current_user.id)
    return {"updated_count": updated}


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


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    current_user: StoredUser = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> None:
    """Permanently delete a notification from the user's inbox."""
    try:
        notification_service.delete_notification(notification_id=notification_id, user_id=current_user.id)
    except NotificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
