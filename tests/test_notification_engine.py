from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from datetime import datetime, timezone, timedelta

from app.schemas.notification import NotificationItem
from app.services.notification_engine import NotificationEngineService, ENGINE_TOPICS


def test_notification_engine_unit_cadence_and_topics():
    # Mock NotificationService
    mock_notif_service = MagicMock()

    def fake_create_notification(*, user_id, title, body, notification_type, metadata=None):
        return NotificationItem(
            id="notif_test_1",
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            metadata=metadata or {},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )

    mock_notif_service.create_notification.side_effect = fake_create_notification

    # Mock AuthStore
    mock_auth_store = MagicMock()
    mock_auth_store.list_all_users.return_value = [
        {"id": "usr_1", "email": "usr1@test.com"},
        {"id": "usr_2", "email": "usr2@test.com"},
    ]

    engine = NotificationEngineService(
        notification_service=mock_notif_service,
        auth_store=mock_auth_store,
    )

    user_id = "test_user_123"

    # 1. Trigger first engine tick (force=True)
    res1 = engine.tick_user(user_id=user_id, force=True)
    assert res1.triggered is True
    assert res1.notification is not None
    assert res1.interval_hours == 2
    assert res1.notification.notification_type in [
        "cycle_alert",
        "ovulation_alert",
        "energy_insight",
        "activity_checkin",
        "learning_tip",
    ]

    # 2. Immediate second tick without force should be blocked by 2-hour cooldown
    res2 = engine.tick_user(user_id=user_id, force=False)
    assert res2.triggered is False
    assert "cooldown" in res2.reason.lower()
    assert res2.next_trigger_in_seconds > 7000  # near 7200s (2 hours)
    assert res2.notification is None

    # 3. Specific topic ticks with force
    for topic in ["period_cycle", "ovulation", "energy", "activity", "learning"]:
        res_topic = engine.tick_user(user_id=user_id, topic=topic, force=True)
        assert res_topic.triggered is True
        assert res_topic.notification is not None

    # 4. Status inspection
    status = engine.get_status(user_id=user_id)
    assert status["interval_hours"] == 2
    assert "last_triggered" in status
    assert "seconds_remaining" in status

    # 5. Broadcast module published
    published = engine.broadcast_module_published(
        module_title="Endometriosis Understanding & Care",
        module_id="mod_endo_101",
        category="Pelvic Care",
        summary="Clinical overview of endometrial tissue, inflammation relief, and gentle lifestyle modifications.",
    )
    assert len(published) == 2
    assert published[0].notification_type == "module_published"
    assert "Endometriosis" in published[0].title
