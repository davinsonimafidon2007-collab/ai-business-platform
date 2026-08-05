"""Tests unitarios para el servicio de alertas por racha de fallos (Task J.1)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.job_failure_alert_service import JobFailureAlertService


@pytest.mark.asyncio
async def test_consecutive_below_threshold_no_send():
    """consecutive < threshold → maybe_notify False, no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=True,
        threshold=3,
        cooldown_hours=6,
        to_email="ops@example.com",
    )
    ok = await svc.maybe_notify(
        job_name="refresh_opportunities",
        consecutive_failures=2,
        failure_count=2,
        last_message="boom",
    )
    assert ok is False
    sender.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_first_alert_at_threshold_sends_once():
    """consecutive >= threshold, primer aviso → True, send 1 vez."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=True,
        threshold=3,
        cooldown_hours=6,
        to_email="ops@example.com",
    )
    ok = await svc.maybe_notify(
        job_name="refresh_opportunities",
        consecutive_failures=3,
        failure_count=3,
        last_message="boom",
    )
    assert ok is True
    sender.send_email.assert_awaited_once()
    # La firma sigue el EmailProvider real
    call_kwargs = sender.send_email.await_args.kwargs
    assert call_kwargs["to_email"] == "ops@example.com"
    assert "refresh_opportunities" in call_kwargs["subject"]
    assert "Consecutive failures: 3" in call_kwargs["body_text"]


@pytest.mark.asyncio
async def test_second_alert_within_cooldown_blocked():
    """Segundo aviso para el mismo job dentro de cooldown → False."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=True,
        threshold=2,
        cooldown_hours=6,
        to_email="ops@example.com",
    )
    assert (
        await svc.maybe_notify(
            job_name="canary", consecutive_failures=2, failure_count=2
        )
        is True
    )
    assert (
        await svc.maybe_notify(
            job_name="canary", consecutive_failures=3, failure_count=3
        )
        is False
    )
    assert sender.send_email.await_count == 1


@pytest.mark.asyncio
async def test_after_cooldown_sends_again():
    """Tras cooldown → True de nuevo."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=True,
        threshold=2,
        cooldown_hours=6,
        to_email="ops@example.com",
    )
    assert (
        await svc.maybe_notify(
            job_name="canary", consecutive_failures=2, failure_count=2
        )
        is True
    )
    # Simular que pasó el cooldown
    svc._last_sent["canary"] = datetime.now(timezone.utc) - timedelta(hours=7)
    assert (
        await svc.maybe_notify(
            job_name="canary", consecutive_failures=2, failure_count=2
        )
        is True
    )
    assert sender.send_email.await_count == 2


@pytest.mark.asyncio
async def test_disabled_no_send():
    """enabled=False → False, no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=False,
        threshold=2,
        to_email="ops@example.com",
    )
    ok = await svc.maybe_notify(
        job_name="canary", consecutive_failures=5, failure_count=5
    )
    assert ok is False
    sender.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_to_email_empty_log_only():
    """to_email='' → True pero solo log (sender no llamado)."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = JobFailureAlertService(
        email_sender=sender,
        enabled=True,
        threshold=2,
        to_email="",
    )
    with patch("app.services.job_failure_alert_service.logger") as mock_log:
        ok = await svc.maybe_notify(
            job_name="canary", consecutive_failures=2, failure_count=2
        )
    assert ok is True
    sender.send_email.assert_not_awaited()
    mock_log.warning.assert_called()
