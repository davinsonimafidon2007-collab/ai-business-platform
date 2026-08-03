"""Envía email cuando una oportunidad supera el umbral (Task C.2).

El servicio comprueba si una oportunidad merece notificación (por
recomendación y/o score mínimo), respeta un cooldown por vehicle_id
para no spamear el mismo vehículo, y envía el email a través del
EmailProvider existente (app/notifications/email_provider.py).

Si no hay EmailProvider inyectado ni SMTP configurado, solo se loguea
(dry-run), siguiendo el patrón del resto del proyecto.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpportunityAlertService:
    """Servicio de notificación por email de oportunidades de compra."""

    # Orden jerárquico de recomendaciones para umbrales.
    _RECOMMENDATION_ORDER: dict[str, int] = {
        "REJECT": 0,
        "CONSIDER": 1,
        "WATCH": 1,
        "BUY": 2,
    }

    def __init__(
        self,
        email_sender: Any | None = None,
        *,
        enabled: bool | None = None,
        min_recommendation: str | None = None,
        min_score: float | None = None,
        cooldown_hours: int | None = None,
    ) -> None:
        """Inicializa el servicio de alertas.

        Args:
            email_sender: Proveedor de email que exponen ``send_email``
                (p.ej. instancia de ``app.notifications.EmailProvider``).
            enabled: Master toggle (default: settings.opportunity_alert_enabled).
            min_recommendation: Recomendación mínima (BUY | CONSIDER).
            min_score: Score mínimo (0 = solo por recomendación).
            cooldown_hours: Cooldown por vehicle_id en horas.
        """
        self._sender = email_sender
        self._enabled = (
            settings.opportunity_alert_enabled if enabled is None else enabled
        )
        self._min_rec = (
            min_recommendation
            or settings.opportunity_alert_min_recommendation
            or "BUY"
        ).upper()
        self._min_score = float(
            min_score
            if min_score is not None
            else getattr(settings, "opportunity_alert_min_score", 0) or 0
        )
        self._cooldown = int(
            cooldown_hours
            if cooldown_hours is not None
            else getattr(settings, "opportunity_alert_cooldown_hours", 24) or 24
        )
        # Memoria de proceso: vehicle_id -> last_sent_at (OK para v1; DB flag en C.2.1)
        self._last_sent: dict[str, datetime] = {}

    # ------------------------------------------------------------------
    # Lógica de umbral
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_recommendation(value: Any) -> str:
        """Normaliza la recommendation a un valor canónico (BUY/CONSIDER/REJECT).

        El motor de evaluación almacena la recommendation como texto
        descriptivo (p.ej. "Vehículo recomendado para importación..."), y el
        ProfitAnalyzer la expone como enum (BUY/CONSIDER/REJECT). Esta función
        soporta ambos formatos.
        """
        rec = str(getattr(value, "value", value) if not isinstance(value, str) else value)
        rec = rec.upper()
        # Enum / valor canónico directo
        if rec in ("BUY", "CONSIDER", "REJECT", "WATCH"):
            return rec
        # Texto descriptivo del EvaluationEngine
        if "RECOMENDADO PARA IMPORTACIÓN" in rec or "REENCOMENDADO PARA" in rec:
            return "BUY"
        if "MARGEN AJUSTADO" in rec or "NEGOCIAR" in rec:
            return "CONSIDER"
        if "NO RECOMENDADO" in rec or "INSUFICIENTE" in rec or "NEGATIVO" in rec:
            return "REJECT"
        # Fallback neutro (no notifica
        return "REJECT"

    def _passes_threshold(self, opportunity: Any) -> bool:
        """Comprueba si la oportunidad supera el umbral configurado."""
        rec = self._normalize_recommendation(
            getattr(opportunity, "recommendation", "") or ""
        )
        score = float(
            getattr(opportunity, "opportunity_score", None)
            or getattr(opportunity, "score", None)
            or 0
        )
        need = self._RECOMMENDATION_ORDER.get(self._min_rec, 2)
        got = self._RECOMMENDATION_ORDER.get(rec, 0)
        if got < need:
            return False
        if self._min_score and score < self._min_score:
            return False
        return True

    def _in_cooldown(self, vehicle_key: str) -> bool:
        """Comprueba si el vehicle_id está en cooldown."""
        last = self._last_sent.get(vehicle_key)
        if not last:
            return False
        return datetime.now(timezone.utc) - last < timedelta(hours=self._cooldown)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def maybe_notify(
        self,
        *,
        user_email: str | None,
        opportunity: Any,
        vehicle: Any | None = None,
    ) -> bool:
        """Envía un email si la oportunidad supera el umbral.

        Devuelve True si se envió (o se logueó como enviado en modo dry).

        Args:
            user_email: Email del dueño del vehículo.
            opportunity: Objeto Opportunity (o similar) con recommendation,
                opportunity_score, estimated_profit, vehicle_id, etc.
            vehicle: Objeto Vehicle (o similar) para contexto en el mensaje.

        Returns:
            True si se notificó, False en caso contrario.
        """
        if not self._enabled:
            return False
        if not self._passes_threshold(opportunity):
            return False
        if not user_email:
            logger.warning("opportunity_alert: sin email de usuario, skip")
            return False

        vid = str(
            getattr(opportunity, "vehicle_id", None)
            or getattr(vehicle, "id", None)
            or getattr(opportunity, "id", "")
        )
        if self._in_cooldown(vid):
            logger.info("opportunity_alert: cooldown vehicle_id=%s", vid)
            return False

        subject, body = self._build_message(opportunity, vehicle)
        await self._send(user_email, subject, body)
        self._last_sent[vid] = datetime.now(timezone.utc)
        return True

    # ------------------------------------------------------------------
    # Construcción y envío del mensaje
    # ------------------------------------------------------------------

    def _build_message(self, opportunity: Any, vehicle: Any | None) -> tuple[str, str]:
        """Construye el asunto y cuerpo (texto) del email."""
        brand = getattr(vehicle, "brand", None) or ""
        model = getattr(vehicle, "model", None) or ""
        price = getattr(vehicle, "price", None)
        rec = getattr(opportunity, "recommendation", "")
        profit = getattr(opportunity, "profit", None) or getattr(
            opportunity, "estimated_profit", None
        )
        roi = getattr(opportunity, "roi", None) or getattr(
            opportunity, "roi_percentage", None
        )
        score = getattr(opportunity, "opportunity_score", None) or getattr(
            opportunity, "score", None
        )
        url = getattr(vehicle, "url", None) or ""

        subject = f"[Oportunidad {rec}] {brand} {model}".strip()
        body = (
            f"Se ha detectado una oportunidad ({rec}).\n\n"
            f"Vehículo: {brand} {model}\n"
            f"Precio: {price}\n"
            f"Score: {score}\n"
            f"Beneficio estimado: {profit}\n"
            f"ROI %: {roi}\n"
            f"URL: {url}\n\n"
            f"— AI Business Platform\n"
        )
        return subject, body

    async def _send(self, to: str, subject: str, body: str) -> None:
        """Envía el email usando el provider inyectado o el default.

        Si no hay SMTP configurado (smtp_host vacío), el EmailProvider
        ya hace logging en lugar de enviar — mismo patrón del proyecto.
        """
        if self._sender is not None and hasattr(self._sender, "send_email"):
            await self._sender.send_email(
                to_email=to, subject=subject, body_html=body, body_text=body
            )
            return

        # Fallback: instanciar el EmailProvider por defecto
        try:
            from app.notifications.email_provider import SmtpEmailProvider

            provider = SmtpEmailProvider()
            await provider.send_email(
                to_email=to, subject=subject, body_html=body, body_text=body
            )
        except Exception:
            # Sin SMTP configurado: solo log (comportamiento del proyecto)
            logger.info(
                "opportunity_alert DRY-RUN to=%s subject=%s\n%s",
                to,
                subject,
                body,
            )