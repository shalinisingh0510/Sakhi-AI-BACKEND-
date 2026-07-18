from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.db import SQLiteAuthStore, SQLiteNotificationStore
from app.services.email import EmailService
from app.services.notifications import NotificationService


class CapturingEmailBackend:
    def __init__(self) -> None:
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        return True


def build_service(database_path: Path) -> tuple[NotificationService, SQLiteAuthStore, CapturingEmailBackend]:
    settings = Settings(database_path=database_path)
    auth_store = SQLiteAuthStore(database_path)
    backend = CapturingEmailBackend()
    email_service = EmailService(backend=backend)
    notification_store = SQLiteNotificationStore(database_path)
    service = NotificationService(
        settings,
        store=notification_store,
        auth_store=auth_store,
        email_service=email_service,
    )
    return service, auth_store, backend


def test_single_notification_sends_email_to_recipient(tmp_path: Path) -> None:
    service, auth_store, backend = build_service(tmp_path / "email-notifications.sqlite3")
    user = auth_store.create_user(
        name="Asha Verma",
        email="asha.verma@sakhi.ai",
        password="StrongPass123!",
        role="user",
    )

    item = service.create_notification(
        user_id=user.id,
        title="Welcome to Sakhi AI",
        body="Thank you for joining our platform!",
        notification_type="announcement",
        metadata={"source": "admin"},
    )

    assert item.title == "Welcome to Sakhi AI"
    assert len(backend.messages) == 1
    message = backend.messages[0]
    assert message.to == "asha.verma@sakhi.ai"
    assert message.subject == "Sakhi AI: Welcome to Sakhi AI"
    assert "Asha Verma" in message.body_text
    assert "Thank you for joining our platform!" in message.body_text


def test_broadcast_notification_sends_email_to_each_user(tmp_path: Path) -> None:
    service, auth_store, backend = build_service(tmp_path / "email-broadcast.sqlite3")
    first_user = auth_store.create_user(
        name="Asha Verma",
        email="asha.verma@sakhi.ai",
        password="StrongPass123!",
        role="user",
    )
    second_user = auth_store.create_user(
        name="Priya Singh",
        email="priya.singh@sakhi.ai",
        password="StrongPass456!",
        role="user",
    )

    notifications = service.create_notifications_for_users(
        user_ids=[first_user.id, second_user.id],
        title="System Maintenance",
        body="We will be performing maintenance tonight.",
        notification_type="system",
    )

    assert len(notifications) == 2
    assert len(backend.messages) == 2
    recipients = {message.to for message in backend.messages}
    assert recipients == {"asha.verma@sakhi.ai", "priya.singh@sakhi.ai"}
