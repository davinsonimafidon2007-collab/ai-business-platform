"""Alertas por racha de fallos de jobs (Task J.1).

El servicio notifica por email cuando un job registrado acumula N fallos
consecutivos (``consecutive_failures >= threshold``), con un cooldown por
``job_name`` para no spamear mientras la racha persiste.

Sigue el patrón de ``OpportunityAlertService`` (C.2): si no hay EmailProvider
inyectado ni SMTP configurado, solo se loguea (dry-run), nunca crashea.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class JobFailureAlertService:
    """Notifica cuando consecutive_failures >= threshold, con cooldown por job name."""

    def __init__(
        self,
        *,
        email_sender: Any | None = None,
        enabled: bool | None = None,
        threshold: int | None = None,
        cooldown_hours: int | None = None,
        to_email: str | None = None,
    ) -> None:
        """Inicializa el servicio de alertas de fallos de jobs.

        Args:
            email_sender: Proveedor de email que expone ``send_email``
                (p.ej. instancia de ``app.notifications.EmailProvider``).
            enabled: Master toggle (default: settings.job_failure_alert_enabled).
            threshold: Racha mínima de fallos para disparar la alerta.
            cooldown_hours: Cooldown por job_name en horas.
            to_email: Dirección ops destino. Vacío -> solo log.
        """
        self._sender = email_sender
        self._enabled = (
            settings.job_failure_alert_enabled if enabled is None else enabled
        )
        self._threshold = int(
            threshold
            if threshold is not None
            else getattr(settings, "job_failure_alert_threshold", 3) or 3
        )
        hours = (
            cooldown_hours
            if cooldown_hours is not None
            else getattr(settings, "job_failure_alert_cooldown_hours", 6) or 6
        )
        self._cooldown = timedelta(hours=int(hours))
        self._to = (
            to_email
            if to_email is not None
            else getattr(settings, "job_failure_alert_to_email", "") or ""
        )
        # Memoria de proceso: job_name -> last_sent_at (OK para v1; Redis en J.1.1)
        self._last_sent: dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def maybe_notify(
        self,
        *,
        job_name: str,
        consecutive_failures: int,
        failure_count: int,
        last_message: str = "",
    ) -> bool:
        """Envía (o loguea) una alerta si la racha supera el umbral.

        Devuelve True si se envió (o se logueó como enviado en modo dry).

        Args:
            job_name: Nombre del job en racha de fallos.
            consecutive_failures: Racha actual de fallos consecutivos.
            failure_count: Total de fallos acumulados.
            last_message: Mensaje del último fallo (contexto).
        """
        if not self._enabled:
            return False
        if int(consecutive_failures) < self._threshold:
            return False

        now = datetime.now(timezone.utc)
        if self._in_cooldown(job_name, now):
            logger.debug(
                "job_failure_alert cooldown job=%s consecutive=%s",
                job_name,
                consecutive_failures,
            )
            return False

        subject = f"[AI Business] Job '{job_name}' failing ({consecutive_failures}x)"
        body = (
            f"Job: {job_name}\n"
            f"Consecutive failures: {consecutive_failures}\n"
            f"Total failures: {failure_count}\n"
            f"Last message: {last_message or '(none)'}\n"
            f"Time (UTC): {now.isoformat()}\n"
        )

        await self._send(subject, body)
        self._last_sent[job_name] = now
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _in_cooldown(self, job_name: str, now: datetime) -> bool:
        last = self._last_sent.get(job_name)
        if not last:
            return False
        return now - last < self._cooldown

    async def _send(self, subject: str, body: str) -> None:
        """Envía el email usando el provider inyectado o el default.

        Si no hay destino configurado ni sender, se loguea un WARNING
        (log-only) — sin crash. La firma sigue el EmailProvider real
        (``to_email``/``subject``/``body_html``/``body_text``).
        """
        if self._to and self._sender is not None and hasattr(self._sender, "send_email"):
            await self._sender.send_email(
                to_email=self._to,
                subject=subject,
                body_html=body,
                body_text=body,
            )
            return

        # Fallback: instanciar el EmailProvider por defecto si hay destino.
        if self._to:
            try:
                from app.notifications.email_provider import SmtpEmailProvider

                provider = SmtpEmailProvider()
                await provider.send_email(
                    to_email=self._to,
                    subject=subject,
                    body_html=body,
                    body_text=body,
                )
            except Exception:
                # Sin SMTP configurado: solo log (comportamiento del proyecto)
                logger.info(
                    "job_failure_alert DRY-RUN to=%s subject=%s\n%s",
                    self._to,
                    subject,
                    body,
                )
            return

        # Sin destino: log-warning (acceptance #6 / FIX 4: to_email="" -> solo log)
        logger.warning(
            "JOB_FAILURE_ALERT (no to_email/sender -> log only): %s\n%s",
            subject,
            body,
        )
