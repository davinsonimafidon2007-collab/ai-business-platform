"""Push notification service — TASK-010 (FASE 5).

Envío de push notifications (FCM) a los tokens registrados de un usuario.
Usa ``PushTokenRepository`` (tokens por user+plataforma) y el Admin SDK
inicializado en ``app.core.firebase``. Si Firebase no está configurado, se
loguea y se devuelve ``skipped=True`` (mismo patrón dry-run del proyecto).
"""

from __future__ import annotations

import logging
import os

from app.core.config import settings
from app.core.firebase import get_firebase_app
from app.database import db_manager

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Servicio de push notifications vía Firebase Cloud Messaging.

    Sigue el patrón de los servicios de alerta del proyecto (OpportunityAlert,
    Telegram): si el canal no está configurado, solo se loguea y se devuelve un
    resultado informativo en lugar de fallar.
    """

    @staticmethod
    def is_configured() -> bool:
        """¿Hay credenciales Firebase y paquete firebase-admin disponibles?"""
        if not (
            getattr(settings, "firebase_credentials_json", "")
            or getattr(settings, "firebase_credentials_path", "")
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        ):
            return False
        return get_firebase_app() is not None

    @staticmethod
    async def send_to_user(
        *,
        user_id: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> dict:
        """Envía una push notification a todos los tokens activos del usuario.

        Args:
            user_id: ID del usuario (UUID string).
            title: Título de la notificación.
            body: Cuerpo de la notificación.
            data: Payload adicional (deepLink, type, ids...).

        Returns:
            Dict con ``sent``/``failed``/``skipped``.
        """
        if not PushNotificationService.is_configured():
            logger.warning("push_service: Firebase no configurado, skip push")
            return {"sent": 0, "failed": 0, "skipped": True}

        async with db_manager.get_session() as session:
            from app.repositories.push_token_repository import PushTokenRepository

            repo = PushTokenRepository(session)
            tokens = await repo.get_by_user_id(user_id)

            if not tokens:
                return {"sent": 0, "failed": 0, "reason": "no_tokens"}

            sent = 0
            failed = 0
            for record in tokens:
                try:
                    PushNotificationService._send_fcm(
                        token=record.token,
                        title=title,
                        body=body,
                        data=data,
                    )
                    sent += 1
                except Exception as exc:  # noqa: BLE001 — por token, no abortar
                    logger.warning(
                        "push_service: fallo en token %s…: %s",
                        record.token[:20],
                        exc,
                    )
                    failed += 1
                    if "registration-token-not-registered" in str(exc).lower():
                        await repo.delete(record)

            return {"sent": sent, "failed": failed}

    @staticmethod
    def _send_fcm(token: str, title: str, body: str, data: dict | None = None) -> None:
        """Envía un único mensaje FCM (bloqueante; FCM Admin SDK es síncrono)."""
        from firebase_admin import messaging

        app = get_firebase_app()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="aibusiness_default",
                    sound="default",
                ),
            ),
        )
        messaging.send(message, app=app)


async def notify_opportunity_created(*, user_id: str, opportunity_data: dict) -> dict:
    """Hook: notifica por push cuando se detecta una oportunidad.

    Título/cuerpo legibles con el vehículo y ROI estimado, payload con
    ``type=opportunity`` para navegación por deep link en el cliente
    (``handleNotificationByType`` en push-notifications.ts).
    """
    brand = opportunity_data.get("brand", "") or ""
    model = opportunity_data.get("model", "") or ""
    roi = opportunity_data.get("roi") or opportunity_data.get("roi_percentage") or "N/A"

    title = "🚗 Nueva oportunidad detectada"
    body = f"{brand} {model}".strip() or "Vehículo"
    if roi != "N/A":
        body += f" — ROI estimado: {roi}"

    return await PushNotificationService.send_to_user(
        user_id=user_id,
        title=title,
        body=body,
        data={
            "type": "opportunity",
            "opportunityId": str(
                opportunity_data.get("id", "")
                or opportunity_data.get("opportunity_id", "")
            ),
        },
    )
