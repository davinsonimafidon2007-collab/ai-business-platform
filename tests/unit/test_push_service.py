"""Tests unitarios para el servicio de push notifications (TASK-010, FASE 5)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.push_service import PushNotificationService, notify_opportunity_created


@pytest.mark.asyncio
async def test_skips_when_firebase_not_configured() -> None:
    """Sin credenciales Firebase → dry-run (skipped=True), no falla."""
    with patch.object(PushNotificationService, "is_configured", return_value=False):
        result = await PushNotificationService.send_to_user(
            user_id="user-1", title="T", body="B"
        )
    assert result == {"sent": 0, "failed": 0, "skipped": True}


@pytest.mark.asyncio
async def test_returns_no_tokens_when_none() -> None:
    """Configurado pero sin tokens registrados → no_tokens."""
    session = MagicMock()
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=[])
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(PushNotificationService, "is_configured", return_value=True),
        patch("app.services.push_service.db_manager") as db_mock,
    ):
        db_mock.get_session.return_value = cm
        with patch(
            "app.repositories.push_token_repository.PushTokenRepository",
            return_value=repo,
        ):
            result = await PushNotificationService.send_to_user(
                user_id="user-1", title="T", body="B"
            )
    assert result == {"sent": 0, "failed": 0, "reason": "no_tokens"}


@pytest.mark.asyncio
async def test_sends_to_all_tokens_and_counts() -> None:
    """Configurado + tokens → envía FCM a todos y cuenta sent/failed."""
    session = MagicMock()
    token_a = MagicMock(token="fcm-token-a")
    token_b = MagicMock(token="fcm-token-b")
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=[token_a, token_b])
    repo.delete = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(PushNotificationService, "is_configured", return_value=True),
        patch("app.services.push_service.db_manager") as db_mock,
    ):
        db_mock.get_session.return_value = cm
        with patch(
            "app.repositories.push_token_repository.PushTokenRepository",
            return_value=repo,
        ):
            with patch.object(
                PushNotificationService, "_send_fcm"
            ) as send_mock:
                result = await PushNotificationService.send_to_user(
                    user_id="user-1",
                    title="Oportunidad",
                    body="BMW 320d — ROI 12%",
                    data={"type": "opportunity"},
                )
    assert result == {"sent": 2, "failed": 0}
    assert send_mock.call_count == 2
    repo.delete.assert_not_called()


@pytest.mark.asyncio
async def test_deactivates_invalid_token() -> None:
    """FCM con token inválido → se cuenta como failed y se elimina el token."""
    session = MagicMock()
    token_a = MagicMock(token="fcm-invalid")
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=[token_a])
    repo.delete = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)

    def raise_unregistered(*_args, **_kwargs) -> None:
        raise Exception("Requested entity was not found: registration-token-not-registered")

    with (
        patch.object(PushNotificationService, "is_configured", return_value=True),
        patch("app.services.push_service.db_manager") as db_mock,
    ):
        db_mock.get_session.return_value = cm
        with patch(
            "app.repositories.push_token_repository.PushTokenRepository",
            return_value=repo,
        ):
            with patch.object(
                PushNotificationService, "_send_fcm", side_effect=raise_unregistered
            ):
                result = await PushNotificationService.send_to_user(
                    user_id="user-1", title="T", body="B"
                )
    assert result == {"sent": 0, "failed": 1}
    repo.delete.assert_awaited_once_with(token_a)


@pytest.mark.asyncio
async def test_notify_opportunity_created_builds_payload() -> None:
    """Hook notify_opportunity_created delega en send_to_user con payload tipo."""
    with patch.object(
        PushNotificationService, "send_to_user", new_callable=AsyncMock
    ) as send_mock:
        send_mock.return_value = {"sent": 1, "failed": 0}
        result = await notify_opportunity_created(
            user_id="user-1",
            opportunity_data={
                "id": "opp-1",
                "brand": "BMW",
                "model": "320d",
                "roi": 12.5,
            },
        )
    send_mock.assert_awaited_once_with(
        user_id="user-1",
        title="🚗 Nueva oportunidad detectada",
        body="BMW 320d — ROI estimado: 12.5",
        data={"type": "opportunity", "opportunityId": "opp-1"},
    )
    assert result == {"sent": 1, "failed": 0}
