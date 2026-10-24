from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_notification_service,
    get_notification_engine,
    pagination_params,
)
from app.schemas.notification import (
    NotificationItem,
    UnreadCountResponse,
    EngineTickRequest,
    EngineTickResponse,
    PublishModuleNotificationRequest,
)
from app.services.auth import StoredUser
from app.services.notifications import NotificationNotFoundError, NotificationService
from app.services.notification_engine import NotificationEngineService, ENGINE_TOPICS

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


@router.post("/engine/tick", response_model=EngineTickResponse)
def engine_tick(
    req: EngineTickRequest | None = None,
    current_user: StoredUser = Depends(get_current_user),
    engine: NotificationEngineService = Depends(get_notification_engine),
) -> EngineTickResponse:
    """
    Evaluates the user's notification engine tick.
    Dispatches rotating 2-hour notifications for period cycle, ovulation, energy, activity, and learning.
    """
    requested_topic = req.topic if req else None
    force_tick = req.force if req else False
    return engine.tick_user(user_id=current_user.id, topic=requested_topic, force=force_tick)


@router.post("/engine/publish-module", response_model=list[NotificationItem])
def publish_module_notification(
    req: PublishModuleNotificationRequest,
    current_user: StoredUser = Depends(get_current_user),
    engine: NotificationEngineService = Depends(get_notification_engine),
) -> list[NotificationItem]:
    """
    Broadcasts a notification to users when a new curriculum module or learning resource is published.
    """
    return engine.broadcast_module_published(req, target_user_id=current_user.id)


@router.get("/engine/status")
def engine_status(
    current_user: StoredUser = Depends(get_current_user),
    engine: NotificationEngineService = Depends(get_notification_engine),
) -> dict:
    """
    Returns the engine cadence status for the active user.
    """
    current_idx = engine._user_topic_index.get(current_user.id, 0)
    next_topic = ENGINE_TOPICS[current_idx % len(ENGINE_TOPICS)]
    last_tick = engine._last_user_tick.get(current_user.id)
    return {
        "engine_active": True,
        "cadence_hours": 2,
        "supported_topics": ENGINE_TOPICS,
        "next_scheduled_topic": next_topic,
        "last_dispatched_at": last_tick.isoformat() if last_tick else None,
    }


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
