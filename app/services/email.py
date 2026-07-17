"""
Email notification service for Sakhi AI.

Two backends are available:
- ConsoleEmailBackend  — prints emails to stdout (default, no config needed).
- SMTPEmailBackend     — sends real emails via SMTP.

Select via settings:
    SAKHI_EMAIL_BACKEND=console   (default)
    SAKHI_EMAIL_BACKEND=smtp
    SAKHI_EMAIL_HOST=smtp.example.com
    SAKHI_EMAIL_PORT=587
    SAKHI_EMAIL_USERNAME=sender@example.com
    SAKHI_EMAIL_PASSWORD=secret
    SAKHI_EMAIL_FROM=noreply@sakhiai.com
    SAKHI_EMAIL_USE_TLS=true
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    body_text: str
    body_html: str | None = None


class EmailBackendProtocol(Protocol):
    def send(self, message: EmailMessage) -> bool:
        """Send an email. Returns True on success, False on failure."""
        ...


class ConsoleEmailBackend:
    """Prints email content to the logger. No external dependencies."""

    def send(self, message: EmailMessage) -> bool:
        logger.info(
            "[EMAIL] To: %s | Subject: %s\n%s",
            message.to,
            message.subject,
            message.body_text,
        )
        return True


class SMTPEmailBackend:
    """
    Sends real email via SMTP with TLS support.
    Falls back to ConsoleEmailBackend on any connection/send error.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str,
        password: str,
        sender: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls
        self._fallback = ConsoleEmailBackend()

    def send(self, message: EmailMessage) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = self._sender
            msg["To"] = message.to

            msg.attach(MIMEText(message.body_text, "plain", "utf-8"))
            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                if self._use_tls:
                    server.starttls(context=context)
                server.login(self._username, self._password)
                server.sendmail(self._sender, message.to, msg.as_string())
            logger.info("Email sent to %s: %s", message.to, message.subject)
            return True
        except Exception as exc:
            logger.warning(
                "SMTP send failed (%s). Falling back to console backend.", exc
            )
            return self._fallback.send(message)


class EmailService:
    """
    High-level email service with predefined notification templates.
    The backend is injected so it can be swapped in tests.
    """

    def __init__(self, backend: EmailBackendProtocol) -> None:
        self._backend = backend

    def send_welcome(self, *, to: str, name: str) -> bool:
        return self._backend.send(
            EmailMessage(
                to=to,
                subject="Welcome to Sakhi AI",
                body_text=(
                    f"Hi {name},\n\n"
                    "Welcome to Sakhi AI — your trusted health education companion.\n\n"
                    "You can now explore lessons, track your progress, and ask health questions "
                    "in your preferred language.\n\n"
                    "Stay healthy,\nThe Sakhi AI Team"
                ),
                body_html=(
                    f"<p>Hi <strong>{name}</strong>,</p>"
                    "<p>Welcome to <strong>Sakhi AI</strong> — your trusted health education companion.</p>"
                    "<p>You can now explore lessons, track your progress, and ask health questions "
                    "in your preferred language.</p>"
                    "<p>Stay healthy,<br>The Sakhi AI Team</p>"
                ),
            )
        )

    def send_password_changed(self, *, to: str, name: str) -> bool:
        return self._backend.send(
            EmailMessage(
                to=to,
                subject="Your Sakhi AI password has been changed",
                body_text=(
                    f"Hi {name},\n\n"
                    "Your account password was recently changed.\n\n"
                    "If you did not make this change, please contact support immediately.\n\n"
                    "The Sakhi AI Team"
                ),
            )
        )

    def send_notification(self, *, to: str, name: str, title: str, body: str) -> bool:
        return self._backend.send(
            EmailMessage(
                to=to,
                subject=f"Sakhi AI: {title}",
                body_text=(
                    f"Hi {name},\n\n"
                    f"{title}\n\n"
                    f"{body}\n\n"
                    "The Sakhi AI Team"
                ),
                body_html=(
                    f"<p>Hi <strong>{name}</strong>,</p>"
                    f"<h3>{title}</h3>"
                    f"<p>{body}</p>"
                    "<p>The Sakhi AI Team</p>"
                ),
            )
        )

    def send_account_deleted(self, *, to: str, name: str) -> bool:
        return self._backend.send(
            EmailMessage(
                to=to,
                subject="Your Sakhi AI account has been deleted",
                body_text=(
                    f"Hi {name},\n\n"
                    "Your Sakhi AI account and all associated data have been permanently deleted.\n\n"
                    "If you did not request this, please contact support.\n\n"
                    "The Sakhi AI Team"
                ),
            )
        )


def build_email_backend(
    backend_name: str = "console",
    *,
    host: str = "",
    port: int = 587,
    username: str = "",
    password: str = "",
    sender: str = "noreply@sakhiai.com",
    use_tls: bool = True,
) -> EmailBackendProtocol:
    """Factory: return the configured email backend."""
    name = backend_name.strip().lower()
    if name == "smtp":
        if not host or not username or not password:
            logger.warning(
                "SAKHI_EMAIL_BACKEND=smtp but host/username/password not fully configured. "
                "Falling back to console backend."
            )
            return ConsoleEmailBackend()
        return SMTPEmailBackend(
            host=host,
            port=port,
            username=username,
            password=password,
            sender=sender,
            use_tls=use_tls,
        )
    if name != "console":
        logger.warning(
            "Unknown email backend '%s'. Using console backend.", backend_name
        )
    return ConsoleEmailBackend()
