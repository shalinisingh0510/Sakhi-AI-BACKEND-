from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.schemas.notification import (
    NotificationItem,
    NotificationType,
    EngineTickResponse,
    PublishModuleNotificationRequest,
)
from app.services.notifications import NotificationService
from app.services.auth import AuthStoreProtocol

logger = logging.getLogger(__name__)

# Topics that rotate every 2 hours
ENGINE_TOPICS = [
    "period_cycle",
    "ovulation",
    "energy",
    "activity",
    "learning",
]

# Clinical message templates
TOPIC_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "period_cycle": [
        {
            "title": "🌸 Cycle Rhythm: Luteal Phase Transition",
            "body": "Progesterone is elevating to support your cycle. If you experience gentle lower back tension, a warm water compress and herbal chamomile tea provide natural relief.",
            "type": "cycle_alert",
            "metadata": {"action_url": "/health/tracker", "cta": "Log Symptoms", "topic": "period_cycle"},
        },
        {
            "title": "🩸 Cycle Literacy: Menstrual Phase Preparation",
            "body": "Your cycle tracker suggests your period is approaching in a few days. Remember to keep extra pads in your bag and prioritize iron-rich leafy greens.",
            "type": "cycle_alert",
            "metadata": {"action_url": "/tools/period-calculator", "cta": "Open Period Calculator", "topic": "period_cycle"},
        },
        {
            "title": "📅 Follicular Vitality",
            "body": "Your follicular phase is beginning! Estrogen is rising, which supports collagen synthesis, clearer skin, and sharper mental clarity.",
            "type": "cycle_alert",
            "metadata": {"action_url": "/health/tracker", "cta": "View Phase Details", "topic": "period_cycle"},
        },
    ],
    "ovulation": [
        {
            "title": "✨ Fertile Window Opening",
            "body": "Your biological rhythm indicates entering your fertile window. Estrogen is reaching peak levels, boosting your natural energy and mood.",
            "type": "ovulation_alert",
            "metadata": {"action_url": "/tools/ovulation-calculator", "cta": "Check Fertile Days", "topic": "ovulation"},
        },
        {
            "title": "🥚 Peak Ovulation Today",
            "body": "Estimated peak ovulation. You may notice subtle bodily cues such as heightened senses and egg-white cervical fluid. A milestone of healthy hormonal rhythm.",
            "type": "ovulation_alert",
            "metadata": {"action_url": "/tools/ovulation-calculator", "cta": "Ovulation Calculator", "topic": "ovulation"},
        },
    ],
    "energy": [
        {
            "title": "⚡ Energy Surge: Estrogen Peak",
            "body": "Mid-follicular energy surge detected! Your metabolic stamina is elevated today—ideal timing for high-focus tasks, creative ideation, and strength training.",
            "type": "energy_insight",
            "metadata": {"action_url": "/dashboard", "cta": "View Energy Forecast", "topic": "energy"},
        },
        {
            "title": "🌙 Energy Wind-Down: Progesterone Support",
            "body": "Progesterone signals rest and recovery. Reduce bright screen exposure 30 minutes before sleep and replenish with magnesium-rich foods like pumpkin seeds.",
            "type": "energy_insight",
            "metadata": {"action_url": "/chat?prompt=How+to+ease+low+energy+during+PMS", "cta": "Ask Sakhi AI", "topic": "energy"},
        },
    ],
    "activity": [
        {
            "title": "💧 Hydration Milestone",
            "body": "Hormonal lymphatic drainage needs steady hydration. Sip a glass of warm water or lemon tea to reduce pelvic bloating and support kidney filtration.",
            "type": "activity_checkin",
            "metadata": {"action_url": "/dashboard", "cta": "Log Water Intake", "topic": "activity"},
        },
        {
            "title": "🧘 Pelvic Care & Gentle Movement",
            "body": "Take a 5-minute break for gentle child's pose and cat-cow breathing. Gentle spinal decompression eases menstrual and pelvic tension.",
            "type": "activity_checkin",
            "metadata": {"action_url": "/learn", "cta": "View Movement Guide", "topic": "activity"},
        },
    ],
    "learning": [
        {
            "title": "📚 Learning Byte: Seed Cycling Balance",
            "body": "Seed cycling (pumpkin and flax seeds during days 1-14, sunflower and sesame seeds in days 15-28) provides essential fatty acids for balanced hormone metabolism.",
            "type": "learning_tip",
            "metadata": {"action_url": "/learn", "cta": "Read Clinical Article", "topic": "learning"},
        },
        {
            "title": "💡 Puberty & Menarche Wisdom",
            "body": "Every body evolves on its own timeline. Learn why menstrual rhythm variations in the first 2-3 years of menarche are completely biologically typical.",
            "type": "learning_tip",
            "metadata": {"action_url": "/learn", "cta": "Explore Puberty Hub", "topic": "learning"},
        },
    ],
}

TOPIC_TEMPLATES_HI: dict[str, list[dict[str, Any]]] = {
    "period_cycle": [
        {
            "title": "🌸 चक्र रिदम: ल्यूटियल फेज़ सहायता",
            "body": "प्रोजेस्टेरोन आपके चक्र को सहारा दे रहा है। यदि पीठ या पेल्विक हिस्से में तनाव महसूस हो, तो गर्म पानी की सिकाई और कैमोमाइल चाय से प्राकृतिक राहत मिलती है।",
            "type": "cycle_alert",
            "metadata": {"action_url": "/health/tracker", "cta": "लक्षण दर्ज करें", "topic": "period_cycle"},
        },
        {
            "title": "🩸 मासिक चक्र: पीरियड की तैयारी",
            "body": "आपके चक्र ट्रैकर के अनुसार कुछ ही दिनों में आपका पीरियड आने वाला है। अपने बैग में पैड रखें और आयरन युक्त हरी पत्तेदार सब्ज़ियों का सेवन करें।",
            "type": "cycle_alert",
            "metadata": {"action_url": "/tools/period-calculator", "cta": "पीरियड कैलकुलेटर खोलें", "topic": "period_cycle"},
        },
        {
            "title": "📅 फॉलिक्युलर स्फूर्ति",
            "body": "आपका फॉलिक्युलर फेज़ शुरू हो रहा है! एस्ट्रोजेन का स्तर बढ़ रहा है, जिससे त्वचा चमकदार और मानसिक एकाग्रता बेहतर होती है।",
            "type": "cycle_alert",
            "metadata": {"action_url": "/health/tracker", "cta": "फेज़ विवरण देखें", "topic": "period_cycle"},
        },
    ],
    "ovulation": [
        {
            "title": "✨ फर्टाइल विंडो शुरू हो रही है",
            "body": "आपकी बायोलॉजिकल रिदम बताती है कि आप फर्टाइल विंडो में प्रवेश कर रहे हैं। एस्ट्रोजेन पीक पर पहुंच रहा है, जिससे प्राकृतिक ऊर्जा और मनोदशा बेहतर होती है।",
            "type": "ovulation_alert",
            "metadata": {"action_url": "/tools/ovulation-calculator", "cta": "फर्टाइल दिन देखें", "topic": "ovulation"},
        },
        {
            "title": "🥚 आज पीक ओव्यूलेशन",
            "body": "अनुमानित पीक ओव्यूलेशन दिन। आप शरीर में प्राकृतिक संकेत जैसे ऊर्जा में वृद्धि महसूस कर सकते हैं। यह स्वस्थ हॉर्मोनल रिदम का संकेत है।",
            "type": "ovulation_alert",
            "metadata": {"action_url": "/tools/ovulation-calculator", "cta": "ओव्यूलेशन कैलकुलेटर", "topic": "ovulation"},
        },
    ],
    "energy": [
        {
            "title": "⚡ ऊर्जा स्तर: एस्ट्रोजेन पीक",
            "body": "फॉलिक्युलर फेज़ में ऊर्जा का स्तर बढ़ रहा है! नए कार्यों, रचनात्मक सोच और एक्टिव रहने के लिए यह सबसे बेहतरीन समय है।",
            "type": "energy_insight",
            "metadata": {"action_url": "/dashboard", "cta": "ऊर्जा पूर्वानुमान देखें", "topic": "energy"},
        },
        {
            "title": "🌙 विश्राम ऊर्जा: प्रोजेस्टेरोन सपोर्ट",
            "body": "प्रोजेस्टेरोन विश्राम और आराम का संकेत देता है। सोने से 30 मिनट पहले स्क्रीन का उपयोग कम करें और कद्दू के बीज जैसे मैग्नीशियम युक्त आहार लें।",
            "type": "energy_insight",
            "metadata": {"action_url": "/chat?prompt=PMS+के+दौरान+कम+ऊर्जा+को+कैसे+संभालें", "cta": "सखी एआई से पूछें", "topic": "energy"},
        },
    ],
    "activity": [
        {
            "title": "💧 हाइड्रेशन माइलस्टोन",
            "body": "हॉर्मोनल संतुलन के लिए सही हाइड्रेशन ज़रूरी है। पेल्विक सूजन कम करने और तरोताज़ा रहने के लिए एक ग्लास गुनगुना पानी पिएं।",
            "type": "activity_checkin",
            "metadata": {"action_url": "/dashboard", "cta": "पानी की मात्रा दर्ज करें", "topic": "activity"},
        },
        {
            "title": "🧘 पेल्विक केयर और सहज योग",
            "body": "5 मिनट का ब्रेक लें और बालासन (Child's pose) व मार्जरी आसन का अभ्यास करें। रीढ़ और पेल्विक क्षेत्र का तनाव कम होता है।",
            "type": "activity_checkin",
            "metadata": {"action_url": "/learn", "cta": "गाइड देखें", "topic": "activity"},
        },
    ],
    "learning": [
        {
            "title": "📚 ज्ञान का संदेश: सीड साइकलिंग संतुलन",
            "body": "सीड साइकलिंग (दिन 1-14 में कद्दू व अलसी, दिन 15-28 में सूरजमुखी व तिल के बीज) हॉर्मोनल संतुलन में प्राकृतिक रूप से मदद करते हैं।",
            "type": "learning_tip",
            "metadata": {"action_url": "/learn", "cta": "लेख पढ़ें", "topic": "learning"},
        },
        {
            "title": "💡 मासिक धर्म और जागरूकता",
            "body": "हर शरीर का अपना अलग समय और गति होती है। पहले 2-3 वर्षों में पीरियड्स का अनियमित होना पूरी तरह सामान्य है।",
            "type": "learning_tip",
            "metadata": {"action_url": "/learn", "cta": "हब देखें", "topic": "learning"},
        },
    ],
}


class NotificationEngineService:
    def __init__(
        self,
        notification_service: NotificationService,
        auth_store: AuthStoreProtocol | None = None,
    ) -> None:
        self._notification_service = notification_service
        self._auth_store = auth_store
        # Track last delivery timestamp per user: {user_id: datetime}
        self._last_user_tick: dict[str, datetime] = {}
        # Track rotating topic index per user: {user_id: int}
        self._user_topic_index: dict[str, int] = {}

    def tick_user(
        self,
        *,
        user_id: str,
        topic: str | None = None,
        force: bool = False,
    ) -> EngineTickResponse:
        """
        Evaluates the user's notification engine cadence.
        Default interval is 2 hours (7200 seconds).
        """
        now = datetime.now(timezone.utc)
        last_tick = self._last_user_tick.get(user_id)

        # 2-hour interval check
        cooldown_seconds = 2 * 3600
        if last_tick and not force:
            elapsed = (now - last_tick).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                current_idx = self._user_topic_index.get(user_id, 0)
                next_topic = ENGINE_TOPICS[current_idx % len(ENGINE_TOPICS)]
                return EngineTickResponse(
                    triggered=False,
                    reason=f"2-Hour cooldown active ({remaining // 60}m {remaining % 60}s remaining).",
                    next_topic=next_topic,
                    next_trigger_in_seconds=remaining,
                    notification=None,
                    interval_hours=2,
                )

        # Select topic
        if topic and topic in TOPIC_TEMPLATES:
            selected_topic = topic
        else:
            current_idx = self._user_topic_index.get(user_id, 0)
            selected_topic = ENGINE_TOPICS[current_idx % len(ENGINE_TOPICS)]
        user = self._auth_store.get_by_id(user_id) if self._auth_store else None
        is_hindi = bool(user and getattr(user, "preferred_language", "").lower() in ("hindi", "hi"))
        template_source = TOPIC_TEMPLATES_HI if is_hindi else TOPIC_TEMPLATES
        templates = template_source.get(selected_topic, template_source["period_cycle"])
        # Rotate sub-template based on current timestamp
        template = templates[int(now.timestamp()) % len(templates)]

        notification = self._notification_service.create_notification(
            user_id=user_id,
            title=template["title"],
            body=template["body"],
            notification_type=template["type"],
            metadata={
                **template.get("metadata", {}),
                "dispatched_by": "notification_engine_v1",
                "cadence_hours": "2",
                "timestamp": now.isoformat(),
            },
        )

        self._last_user_tick[user_id] = now
        next_idx = self._user_topic_index.get(user_id, 0)
        next_topic = ENGINE_TOPICS[next_idx % len(ENGINE_TOPICS)]

        return EngineTickResponse(
            triggered=True,
            reason=f"Dispatched {selected_topic} alert for 2-hour cadence.",
            next_topic=next_topic,
            next_trigger_in_seconds=cooldown_seconds,
            notification=notification,
            interval_hours=2,
        )

    def get_status(self, user_id: str) -> dict[str, Any]:
        """
        Returns the cadence status for a user, including next topic and cooldown remaining.
        """
        current_idx = self._user_topic_index.get(user_id, 0)
        next_topic = ENGINE_TOPICS[current_idx % len(ENGINE_TOPICS)]
        last_tick = self._last_user_tick.get(user_id)
        
        seconds_remaining = 0
        if last_tick:
            elapsed = (datetime.now(timezone.utc) - last_tick).total_seconds()
            seconds_remaining = max(0, int(2 * 3600 - elapsed))

        return {
            "engine_active": True,
            "cadence_hours": 2,
            "interval_hours": 2,
            "supported_topics": ENGINE_TOPICS,
            "next_scheduled_topic": next_topic,
            "last_triggered": last_tick.isoformat() if last_tick else None,
            "seconds_remaining": seconds_remaining,
        }

    def broadcast_module_published(
        self,
        request: PublishModuleNotificationRequest | None = None,
        *,
        module_title: str | None = None,
        module_id: str | None = None,
        category: str | None = None,
        summary: str | None = None,
        target_user_id: str | None = None,
    ) -> list[NotificationItem]:
        """
        Broadcasts a 'module_published' notification to users when a new curriculum module is released.
        """
        title_str = (request.module_title if request else module_title) or "Curriculum Update"
        cat_str = (request.category if request else category) or "Education"
        mod_id = (request.module_id if request else module_id) or "module"
        sum_str = (request.summary if request else summary) or f"Explore '{title_str}' in {cat_str}."

        title = f"🎉 New Module Published: {title_str}"
        body = sum_str

        metadata = {
            "topic": "module_published",
            "module_id": mod_id,
            "category": cat_str,
            "action_url": f"/learn?module={mod_id}",
            "cta": "Start Learning",
        }

        # If target user specified, send to that user
        if target_user_id:
            item = self._notification_service.create_notification(
                user_id=target_user_id,
                title=title,
                body=body,
                notification_type="module_published",
                metadata=metadata,
            )
            return [item]

        # Broadcast to all users in auth store if available
        created: list[NotificationItem] = []
        if self._auth_store:
            try:
                users = []
                if hasattr(self._auth_store, "list_all_users"):
                    users = self._auth_store.list_all_users()
                elif hasattr(self._auth_store, "list_users"):
                    users = self._auth_store.list_users()

                for u in users:
                    uid = u["id"] if isinstance(u, dict) else getattr(u, "id", None)
                    u_lang = (u.get("preferred_language") if isinstance(u, dict) else getattr(u, "preferred_language", "")) or ""
                    is_hi = u_lang.lower() in ("hindi", "hi")
                    user_title = f"🎉 नया मॉड्यूल प्रकाशित: {title_str}" if is_hi else title
                    user_meta = {**metadata, "cta": "सीखना शुरू करें" if is_hi else "Start Learning"}
                    if uid:
                        notif = self._notification_service.create_notification(
                            user_id=uid,
                            title=user_title,
                            body=body,
                            notification_type="module_published",
                            metadata=user_meta,
                        )
                        created.append(notif)
            except Exception as e:
                logger.warning(f"Broadcast lookup error: {e}")

        # Fallback to single/system notification if no store users
        if not created and target_user_id:
            created.append(
                self._notification_service.create_notification(
                    user_id=target_user_id,
                    title=title,
                    body=body,
                    notification_type="module_published",
                    metadata=metadata,
                )
            )

        return created

