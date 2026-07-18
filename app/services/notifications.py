from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from app.core.config import Settings
from app.schemas.notification import NotificationItem, NotificationType
from app.services.auth import AuthStoreProtocol
from app.services.email import EmailService

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

    def mark_all_as_read(self, *, user_id: str) -> int:
        """Mark all unread notifications as read. Returns the count of updated rows."""
        ...

    def delete_notification(self, *, notification_id: str, user_id: str) -> None:
        ...


class NotificationService:
    def __init__(
        self,
        settings: Settings,
        store: NotificationStoreProtocol,
        auth_store: AuthStoreProtocol | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._settings = settings
        self._store = store
        self._auth_store = auth_store
        self._email_service = email_service

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
        self._send_email_notification(user_id=user_id, item=item)
        # Push real-time update over WebSocket if the user is connected
        self._push_realtime(user_id, item)
        return item

    def _send_email_notification(self, *, user_id: str, item: NotificationItem) -> None:
        if self._auth_store is None or self._email_service is None:
            return

        try:
            user = self._auth_store.get_by_id(user_id)
            if user is None or not getattr(user, "email", ""):
                return
            self._email_service.send_notification(
                to=user.email,
                name=user.name,
                title=item.title,
                body=item.body,
            )
        except Exception as exc:
            logger.warning("Email notification delivery failed: %s", exc)

    def _push_realtime(self, user_id: str, item: NotificationItem) -> None:
        """Fire-and-forget WebSocket push. Never raises."""
        try:
            from app.core.websocket_manager import ws_manager  # avoid circular import at module load

            payload = {"type": "notification", "data": item.model_dump(mode="json")}
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            loop.create_task(ws_manager.send_notification(user_id, payload))
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

    def mark_all_as_read(self, *, user_id: str) -> int:
        """Mark every unread notification as read. Returns updated count."""
        return self._store.mark_all_as_read(user_id=user_id)

    def delete_notification(self, *, notification_id: str, user_id: str) -> None:
        """Delete a single notification. Raises NotificationNotFoundError if not found."""
        self._store.delete_notification(notification_id=notification_id, user_id=user_id)
