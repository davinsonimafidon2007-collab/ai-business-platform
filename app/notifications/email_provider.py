from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email sending providers."""

    @abstractmethod
    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Send an email via the configured provider.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            body_html: HTML body content.
            body_text: Plain text fallback body content.
        """
        ...


class SmtpEmailProvider(EmailProvider):
    """SMTP-based email provider with real sending capability.

    Configured via environment variables:
    - SMTP_HOST: SMTP server hostname (default: localhost)
    - SMTP_PORT: SMTP server port (default: 587)
    - SMTP_USER: SMTP username
    - SMTP_PASSWORD: SMTP password
    - SMTP_FROM_EMAIL: From email address (default: noreply@example.com)
    - SMTP_USE_TLS: Use TLS (default: True)

    If SMTP_HOST is not set, emails are logged instead of sent.
    """

    def __init__(self) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.use_tls = settings.smtp_use_tls

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Send an email via SMTP or log it if not configured."""
        if not self.host:
            logger.info(
                "SMTP not configured. Email would be sent:\n"
                "  To:       %s\n"
                "  Subject:  %s\n"
                "  Body:\n%s",
                to_email,
                subject,
                body_text or body_html,
            )
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        try:
            if self.use_tls:
                await aiosmtplib.send(
                    msg,
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    use_tls=True,
                )
            else:
                await aiosmtplib.send(
                    msg,
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    start_tls=True,
                )
            logger.info("Email sent successfully to %s: %s", to_email, subject)
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)
            raise

