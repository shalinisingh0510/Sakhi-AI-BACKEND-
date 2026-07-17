from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Protocol
from uuid import uuid4
import json

from app.core.config import Settings
from app.schemas.notification import NotificationItem, NotificationType

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Base exception for notification failures."""


class NotificationNotFoundError(NotificationError):
    pass


class InvalidNotificationError(NotificationError):
    pass


@dataclass(slots=True)
class StoredNotification:
    id: str
    user_id: str
    title: str
    body: str
    notification_type: str
    metadata: dict[str, str]
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    def to_item(self) -> NotificationItem:
        return NotificationItem.model_validate(self)


class NotificationStoreProtocol(Protocol):
    def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        notification_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredNotification:
        ...

    def list_notifications(self, *, user_id: str, unread_only: bool = False) -> list[StoredNotification]:
        ...

    def count_unread(self, *, user_id: str) -> int:
        ...

    def mark_as_read(self, *, notification_id: str, user_id: str) -> StoredNotification:
        ...


class NotificationService:
    def __init__(self, settings: Settings, store: NotificationStoreProtocol) -> None:
        self._settings = settings
        self._store = store

    def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        notification_type: NotificationType = "announcement",
        metadata: dict[str, str] | None = None,
    ) -> NotificationItem:
        record = self._store.create_notification(
            user_id=user_id,
            title=title.strip(),
            body=body.strip(),
            notification_type=notification_type,
            metadata=metadata or {},
        )
        item = record.to_item()
        # Push real-time update over WebSocket if the user is connected
        self._push_realtime(user_id, item)
        return item

    def _push_realtime(self, user_id: str, item: NotificationItem) -> None:
        """Fire-and-forget WebSocket push. Never raises."""
        try:
            from app.core.websocket_manager import ws_manager  # avoid circular import at module load

            payload = {"type": "notification", "data": item.model_dump(mode="json")}
            # Run in the current event loop if one is running, otherwise skip.
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(ws_manager.send_notification(user_id, payload))
            except RuntimeError:
                pass  # No event loop — sync context (e.g. tests); skip push
        except Exception as exc:
            logger.warning("Real-time notification push failed: %s", exc)

    def create_notifications_for_users(
        self,
        *,
        user_ids: list[str],
        title: str,
        body: str,
        notification_type: NotificationType = "announcement",
        metadata: dict[str, str] | None = None,
    ) -> list[NotificationItem]:
        notifications: list[NotificationItem] = []
        for user_id in user_ids:
            notifications.append(
                self.create_notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    metadata=metadata,
                )
            )
        return notifications

    def create_lesson_completion_notification(
        self,
        *,
        user_id: str,
        lesson_title: str,
        lesson_slug: str,
    ) -> NotificationItem:
        return self.create_notification(
            user_id=user_id,
            title=f"Lesson completed: {lesson_title}",
            body=f"You completed {lesson_title}. You can revisit it anytime from your progress history.",
            notification_type="lesson_completed",
            metadata={"lesson_slug": lesson_slug, "lesson_title": lesson_title},
        )

    def list_notifications(self, *, user_id: str, unread_only: bool = False) -> list[NotificationItem]:
        return [notification.to_item() for notification in self._store.list_notifications(user_id=user_id, unread_only=unread_only)]

    def count_unread(self, *, user_id: str) -> int:
        return self._store.count_unread(user_id=user_id)

    def mark_as_read(self, *, notification_id: str, user_id: str) -> NotificationItem:
        try:
            record = self._store.mark_as_read(notification_id=notification_id, user_id=user_id)
        except RuntimeError as exc:
            raise NotificationNotFoundError(str(exc)) from exc
        return record.to_item()

