"""Tests unitarios para el servicio de alertas de oportunidades (Task C.2)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.opportunity_alert_service import OpportunityAlertService


@pytest.mark.asyncio
async def test_notify_buy_sends_email():
    """BUY + email válido + SMTP/mock → se envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
        cooldown_hours=24,
    )
    opp = MagicMock(
        recommendation="BUY",
        opportunity_score=90,
        vehicle_id="v1",
        estimated_profit=2000,
    )
    vehicle = MagicMock(id="v1", brand="BMW", model="320d", price=18000, url="http://x")
    ok = await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=vehicle)
    assert ok is True
    sender.send_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_does_not_send():
    """REJECT → no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
    )
    opp = MagicMock(recommendation="REJECT", opportunity_score=10, vehicle_id="v2")
    ok = await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=None)
    assert ok is False
    sender.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_cooldown_prevents_second_send():
    """Segundo BUY mismo vehicle_id dentro de cooldown → no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
        cooldown_hours=24,
    )
    opp = MagicMock(recommendation="BUY", opportunity_score=90, vehicle_id="v1")
    vehicle = MagicMock(id="v1", brand="Audi", model="A4", price=1, url="")
    assert (
        await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=vehicle)
        is True
    )
    assert (
        await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=vehicle)
        is False
    )
    assert sender.send_email.await_count == 1


@pytest.mark.asyncio
async def test_disabled_does_not_send():
    """OPPORTUNITY_ALERT_ENABLED=false → no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=False,
        min_recommendation="BUY",
    )
    opp = MagicMock(recommendation="BUY", opportunity_score=90, vehicle_id="v3")
    ok = await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=None)
    assert ok is False
    sender.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_recommendation_normalized():
    """Recomendación en formato texto del EvaluationEngine → BUY → envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
    )
    opp = MagicMock(
        recommendation="Vehículo recomendado para importación. El margen de beneficio es adecuado.",
        opportunity_score=85,
        vehicle_id="v4",
    )
    vehicle = MagicMock(id="v4", brand="Seat", model="Leon", price=15000, url="")
    ok = await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=vehicle)
    assert ok is True
    sender.send_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_consider_with_min_buy_does_not_send():
    """CONSIDER con umbral BUY → no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
    )
    opp = MagicMock(recommendation="CONSIDER", opportunity_score=60, vehicle_id="v5")
    ok = await svc.maybe_notify(user_email="a@b.com", opportunity=opp, vehicle=None)
    assert ok is False
    sender.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_user_email_does_not_send():
    """Sin email de usuario → skip con warning, no envía."""
    sender = MagicMock()
    sender.send_email = AsyncMock()
    svc = OpportunityAlertService(
        email_sender=sender,
        enabled=True,
        min_recommendation="BUY",
    )
    opp = MagicMock(recommendation="BUY", opportunity_score=90, vehicle_id="v6")
    ok = await svc.maybe_notify(user_email=None, opportunity=opp, vehicle=None)
    assert ok is False
    sender.send_email.assert_not_awaited()