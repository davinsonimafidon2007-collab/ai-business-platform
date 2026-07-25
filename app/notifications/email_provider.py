from __future__ import annotations

from abc import ABC, abstractmethod


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
    """SMTP-based email provider (placeholder for future integration).

    This class is prepared but not yet connected to a real SMTP server.
    It logs emails instead of sending them, allowing the system to be
    tested without a real email provider.

    To activate real sending, configure SMTP_* environment variables
    and implement the connection logic inside ``send_email``.
    """

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
    ) -> None:
        """Log the email and prepare for future SMTP integration."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "Email would be sent — SMTP not yet configured.\n"
            "  To:       %s\n"
            "  Subject:  %s\n"
            "  Body:\n%s",
            to_email,
            subject,
            body_text or body_html,
        )