"""Tests unitarios para TelegramAlertService (Task C.3).

No se usan tokens reales: todo se inyecta por constructor y se mockea
``httpx.AsyncClient`` para verificar endpoint, payload y manejo de errores.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.telegram_alert_service import TelegramAlertService


def _svc(**kwargs) -> TelegramAlertService:
    """Servicio con credenciales de test por defecto (dry-run)."""
    defaults = dict(
        telegram_bot_token="",
        telegram_chat_id="",
        enabled=True,
        min_recommendation="BUY",
        min_score=0,
        min_margin_percent=0,
        cooldown_hours=6,
    )
    defaults.update(kwargs)
    return TelegramAlertService(**defaults)


def _opp(**kwargs) -> MagicMock:
    opp = MagicMock()
    opp.recommendation = "BUY"
    opp.opportunity_score = 90
    opp.vehicle_id = "v1"
    opp.profit = 3000.0
    opp.roi = 25.0
    for k, v in kwargs.items():
        setattr(opp, k, v)
    return opp


def _vehicle(**kwargs) -> MagicMock:
    v = MagicMock()
    v.id = "v1"
    v.brand = "Toyota"
    v.model = "Corolla"
    v.price = 12000.0
    v.source = "autoscout24"
    v.url = "https://example.com/v1"
    v.user_id = "u1"
    for k, val in kwargs.items():
        setattr(v, k, val)
    return v


def _evaluation(**kwargs) -> MagicMock:
    ev = MagicMock()
    ev.estimated_total_cost = 16500.0
    ev.estimated_market_price_es = 21000.0
    ev.estimated_profit = 4500.0
    ev.profit_margin_percent = 27.3
    ev.score = 88
    for k, v in kwargs.items():
        setattr(ev, k, v)
    return ev


class _FakeResp:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


def _mock_http_client(status_code=200, text="ok", post_exc=None) -> MagicMock:
    """Construye un httpx.AsyncClient mockeado como async context manager."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    if post_exc is not None:
        client.post = AsyncMock(side_effect=post_exc)
    else:
        client.post = AsyncMock(return_value=_FakeResp(status_code, text))
    return client


# =============================================================================
# Dry-run / umbrales / cooldown
# =============================================================================


@pytest.mark.asyncio
async def test_dry_run_no_credentials_no_http():
    """Sin bot_token/chat_id: dry-run, no petición HTTP."""
    svc = _svc()
    with patch("app.services.telegram_alert_service.httpx.AsyncClient") as client_cls:
        ok = await svc.send_opportunity_alert(
            opportunity=_opp(), vehicle=_vehicle()
        )
    assert ok is True
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_does_not_send():
    """enabled=False → False, ni dry-run ni http."""
    svc = _svc(enabled=False, telegram_bot_token="token", telegram_chat_id="-100")
    with patch("app.services.telegram_alert_service.httpx.AsyncClient") as client_cls:
        ok = await svc.send_opportunity_alert(
            opportunity=_opp(), vehicle=_vehicle()
        )
    assert ok is False
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_reject_recommendation_does_not_send():
    """REJECT con umbral BUY → no envía."""
    svc = _svc(telegram_bot_token="token", telegram_chat_id="-100")
    with patch("app.services.telegram_alert_service.httpx.AsyncClient") as client_cls:
        ok = await svc.send_opportunity_alert(
            opportunity=_opp(recommendation="REJECT"),
            vehicle=_vehicle(),
        )
    assert ok is False
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_min_score_filters():
    """opportunity_score < min_score → no envía."""
    svc = _svc(min_score=95, telegram_bot_token="token", telegram_chat_id="-100")
    with patch("app.services.telegram_alert_service.httpx.AsyncClient") as client_cls:
        ok = await svc.send_opportunity_alert(
            opportunity=_opp(opportunity_score=80), vehicle=_vehicle()
        )
    assert ok is False
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_min_margin_filters_by_roi():
    """roi < min_margin_percent → no envía."""
    svc = _svc(min_margin_percent=30.0, telegram_bot_token="token", telegram_chat_id="-100")
    with patch("app.services.telegram_alert_service.httpx.AsyncClient") as client_cls:
        ok = await svc.send_opportunity_alert(
            opportunity=_opp(roi=20.0), vehicle=_vehicle()
        )
    assert ok is False
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_cooldown_prevents_second_send():
    """Segundo aviso mismo vehicle_id dentro de cooldown → False, http 1 vez."""
    svc = _svc(cooldown_hours=24, telegram_bot_token="token", telegram_chat_id="-100")
    with patch(
        "app.services.telegram_alert_service.httpx.AsyncClient",
        return_value=_mock_http_client(),
    ) as client_cls:
        opp = _opp()
        vehicle = _vehicle()
        first = await svc.send_opportunity_alert(opportunity=opp, vehicle=vehicle)
        second = await svc.send_opportunity_alert(opportunity=opp, vehicle=vehicle)
    assert first is True
    assert second is False
    client_cls.return_value.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_after_cooldown_sends_again():
    """Tras cooldown → True de nuevo, http llamado 2 veces."""
    svc = _svc(cooldown_hours=1, telegram_bot_token="token", telegram_chat_id="-100")
    client = _mock_http_client()
    with patch("app.services.telegram_alert_service.httpx.AsyncClient", return_value=client):
        opp = _opp()
        vehicle = _vehicle()
        await svc.send_opportunity_alert(opportunity=opp, vehicle=vehicle)
        # forzar cooldown expirado
        from datetime import UTC, datetime, timedelta

        svc._last_sent["v1"] = datetime.now(UTC) - timedelta(hours=2)
        ok = await svc.send_opportunity_alert(opportunity=opp, vehicle=vehicle)
    assert ok is True
    assert client.post.await_count == 2


# =============================================================================
# Envío correcto (endpoint, payload, formato)
# =============================================================================


@pytest.mark.asyncio
async def test_sends_to_correct_endpoint_and_payload():
    """Con credenciales → POST a /sendMessage con parse_mode HTML y chat_id."""
    svc = _svc(telegram_bot_token="MYTOKEN", telegram_chat_id="-100123")
    client = _mock_http_client()
    with patch("app.services.telegram_alert_service.httpx.AsyncClient", return_value=client):
        ok = await svc.send_opportunity_alert(opportunity=_opp(), vehicle=_vehicle())
    assert ok is True

    client.post.assert_awaited_once()
    args, kwargs = client.post.await_args
    assert args[0] == "https://api.telegram.org/botMYTOKEN/sendMessage"
    payload = kwargs["json"]
    assert payload["chat_id"] == "-100123"
    assert payload["parse_mode"] == "HTML"
    assert payload["disable_web_page_preview"] is True
    text = payload["text"]
    assert "<b>Toyota Corolla</b>" in text
    assert "<a href=" in text and ">Ver anuncio</a>" in text
    assert "Autoscout24 (DE)" in text
    assert "25.00 %" in text  # ROI


@pytest.mark.asyncio
async def test_message_contains_estimated_costs_when_evaluation():
    """Con VehicleEvaluation/resultado: incluye costes, market y margen."""
    svc = _svc(telegram_bot_token="tok", telegram_chat_id="chat")
    client = _mock_http_client()
    with patch("app.services.telegram_alert_service.httpx.AsyncClient", return_value=client):
        await svc.send_opportunity_alert(
            opportunity=_opp(), vehicle=_vehicle(), evaluation=_evaluation()
        )
    text = client.post.await_args.kwargs["json"]["text"]
    assert "Coste total estimado: 16.500,00 €" in text
    assert "Valor de mercado (ES): 21.000,00 €" in text
    assert "Margen neto: 27.30 %" in text


# =============================================================================
# HTML escaping
# =============================================================================


def test_html_escaping_in_message():
    """brand/model/url con markup no deben inyectar HTML en el mensaje."""
    svc = _svc()
    evil = _vehicle(
        brand="<script>alert(1)</script>",
        model='"><b>bold</b>',
        url='https://x.com/p?a=1&b=2";evil',
    )
    opp = _opp(recommendation="BUena oportunidad")
    text = svc._build_telegram_message(opp, evil, None)
    # El markup inyectado debe estar escapado, no como etiqueta viva.
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text
    assert "<b>bold</b>" not in text  # el <b> inyectado debe escaparse
    assert "&quot;" in text or "&gt;" in text
    # La URL escapada no cierra la etiqueta <a>.
    assert '";evil' not in text


# =============================================================================
# Manejo de errores de la API
# =============================================================================


@pytest.mark.asyncio
async def test_telegram_api_error_does_not_raise():
    """Respuesta HTTP 500: no propaga, dry-run sigue True (loguea)."""
    svc = _svc(telegram_bot_token="tok", telegram_chat_id="chat")
    with patch(
        "app.services.telegram_alert_service.httpx.AsyncClient",
        return_value=_mock_http_client(status_code=500, text="server error"),
    ):
        ok = await svc.send_opportunity_alert(opportunity=_opp(), vehicle=_vehicle())
    assert ok is True  # se "envió" (logueó) sin lanzar


@pytest.mark.asyncio
async def test_http_exception_does_not_raise():
    """httpx.HTTPError durante el POST: no propaga al caller."""
    svc = _svc(telegram_bot_token="tok", telegram_chat_id="chat")
    with patch(
        "app.services.telegram_alert_service.httpx.AsyncClient",
        return_value=_mock_http_client(post_exc=httpx.ConnectError("boom")),
    ):
        ok = await svc.send_opportunity_alert(opportunity=_opp(), vehicle=_vehicle())
    assert ok is True
