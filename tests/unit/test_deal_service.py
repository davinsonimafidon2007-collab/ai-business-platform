"""Tests del servicio de deals (Task D.1): transiciones y ownership."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.deal import Deal, DealStatus
from app.services.deal_service import DealService


def _make_deal(
    *,
    deal_id: str = "deal-1",
    user_id: str = "user-1",
    status: DealStatus = DealStatus.NEW,
) -> Deal:
    return Deal(
        id=deal_id,
        user_id=user_id,
        status=status,
    )


def _make_service(
    deal: Deal, active_for_opportunity: Deal | None = None
) -> DealService:
    repo = AsyncMock()
    repo.get_by_id.return_value = deal
    repo.update.return_value = deal
    repo.create.return_value = deal
    repo.get_active_by_opportunity.return_value = active_for_opportunity
    return DealService(repo)


@pytest.mark.asyncio
async def test_create_requires_opportunity_or_vehicle() -> None:
    """Sin opportunity_id ni vehicle_id -> 422."""
    service = _make_service(_make_deal())
    with pytest.raises(HTTPException) as exc:
        await service.create(user_id="user-1")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_ok_with_opportunity() -> None:
    """Con opportunity_id -> crea deal en estado NEW."""
    deal = _make_deal()
    service = _make_service(deal)
    result = await service.create(user_id="user-1", opportunity_id="opp-1")
    assert result.status == DealStatus.NEW


@pytest.mark.asyncio
async def test_create_ok_with_vehicle() -> None:
    """Con vehicle_id -> crea deal en estado NEW."""
    deal = _make_deal()
    service = _make_service(deal)
    result = await service.create(user_id="user-1", vehicle_id="vehicle-1")
    assert result.status == DealStatus.NEW


@pytest.mark.asyncio
async def test_create_duplicate_active_opportunity_conflict() -> None:
    """Segundo create con misma opportunity activa -> 409 (Task D.3)."""
    existing = _make_deal(deal_id="deal-existing", status=DealStatus.OFFER)
    service = _make_service(_make_deal(), active_for_opportunity=existing)
    with pytest.raises(HTTPException) as exc:
        await service.create(user_id="user-1", opportunity_id="opp-1")
    assert exc.value.status_code == 409
    assert exc.value.detail["deal_id"] == "deal-existing"


@pytest.mark.asyncio
async def test_create_after_terminal_allowed() -> None:
    """Tras WON/LOST/DROPPED, nuevo create -> permitido (nuevo ciclo)."""
    deal = _make_deal()
    service = _make_service(deal, active_for_opportunity=None)
    result = await service.create(user_id="user-1", opportunity_id="opp-1")
    assert result.status == DealStatus.NEW


@pytest.mark.asyncio
async def test_transition_new_to_contacted_ok() -> None:
    """NEW -> CONTACTED es válido."""
    deal = _make_deal(status=DealStatus.NEW)
    service = _make_service(deal)
    result = await service.transition(
        deal_id="deal-1",
        user_id="user-1",
        new_status=DealStatus.CONTACTED,
    )
    assert result.status == DealStatus.CONTACTED


@pytest.mark.asyncio
async def test_transition_new_to_won_illegal() -> None:
    """NEW -> WON es ilegal (422)."""
    deal = _make_deal(status=DealStatus.NEW)
    service = _make_service(deal)
    with pytest.raises(HTTPException) as exc:
        await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.WON,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_transition_terminal_rejected() -> None:
    """WON -> cualquier salida es ilegal (422)."""
    deal = _make_deal(status=DealStatus.WON)
    service = _make_service(deal)
    with pytest.raises(HTTPException) as exc:
        await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.CONTACTED,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_transition_offer_to_won_ok() -> None:
    """OFFER -> WON es válido y guarda offer_price."""
    deal = _make_deal(status=DealStatus.OFFER)
    service = _make_service(deal)
    result = await service.transition(
        deal_id="deal-1",
        user_id="user-1",
        new_status=DealStatus.WON,
        offer_price=12000.0,
    )
    assert result.status == DealStatus.WON
    assert result.offer_price == 12000.0


@pytest.mark.asyncio
async def test_transition_ownership_rejected() -> None:
    """Transición sobre deal ajeno -> 404."""
    deal = _make_deal(user_id="user-2", status=DealStatus.NEW)
    service = _make_service(deal)
    with pytest.raises(HTTPException) as exc:
        await service.transition(
            deal_id="deal-1",
            user_id="user-1",
            new_status=DealStatus.CONTACTED,
        )
    assert exc.value.status_code == 404
