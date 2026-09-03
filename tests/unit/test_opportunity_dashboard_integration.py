"""Tests de integración para Dashboard + Opportunity Integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.opportunity import OpportunityStatus
from app.services.dashboard_service import DashboardService
from app.services.opportunity_integration_service import OpportunityIntegrationService


@pytest.mark.asyncio
async def test_dashboard_summary():
    d = DashboardService()
    result = await d.get_summary()
    assert result["status"] == "operational"


def _make_opportunity(
    *,
    opportunity_id: str = "opp-1",
    user_id: str = "user_1",
    recommendation: str = "BUY_NOW",
    opp_status: str = OpportunityStatus.OPEN.value,
) -> MagicMock:
    vehicle = MagicMock(user_id=user_id)
    return MagicMock(
        id=opportunity_id,
        vehicle=vehicle,
        vehicle_id="vehicle-1",
        recommendation=recommendation,
        status=opp_status,
    )


@pytest.mark.asyncio
async def test_opportunity_integration_creates_deal_for_buy_now():
    """TASK 3 (AUD-011): la conversión real crea un deal y marca CONVERTED."""
    opportunity = _make_opportunity()
    repo = AsyncMock()
    repo.get.return_value = opportunity
    repo.save = AsyncMock()

    deal_service = AsyncMock()
    deal_service.create.return_value = MagicMock(id="deal-1")

    service = OpportunityIntegrationService(
        opportunity_repository=repo, deal_service=deal_service
    )
    deal = await service.convert_to_deal(opportunity_id="opp-1", user_id="user_1")

    assert deal.id == "deal-1"
    deal_service.create.assert_awaited_once()
    call_kwargs = deal_service.create.await_args.kwargs
    assert call_kwargs["opportunity_id"] == "opp-1"
    assert call_kwargs["vehicle_id"] == "vehicle-1"
    assert opportunity.status == OpportunityStatus.CONVERTED.value
    repo.save.assert_awaited_once_with(opportunity)


@pytest.mark.asyncio
async def test_opportunity_integration_rejects_watch_recommendation():
    """WATCH/REJECT no justifican crear un deal -> 422."""
    from fastapi import HTTPException

    opportunity = _make_opportunity(recommendation="WATCH")
    repo = AsyncMock()
    repo.get.return_value = opportunity
    deal_service = AsyncMock()

    service = OpportunityIntegrationService(
        opportunity_repository=repo, deal_service=deal_service
    )
    with pytest.raises(HTTPException) as exc:
        await service.convert_to_deal(opportunity_id="opp-1", user_id="user_1")
    assert exc.value.status_code == 422
    deal_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_opportunity_integration_rejects_already_converted():
    """Una oportunidad ya convertida no puede volver a convertirse -> 409."""
    from fastapi import HTTPException

    opportunity = _make_opportunity(opp_status=OpportunityStatus.CONVERTED.value)
    repo = AsyncMock()
    repo.get.return_value = opportunity
    deal_service = AsyncMock()

    service = OpportunityIntegrationService(
        opportunity_repository=repo, deal_service=deal_service
    )
    with pytest.raises(HTTPException) as exc:
        await service.convert_to_deal(opportunity_id="opp-1", user_id="user_1")
    assert exc.value.status_code == 409
    deal_service.create.assert_not_called()


@pytest.mark.asyncio
async def test_opportunity_integration_rejects_foreign_opportunity():
    """Oportunidad de otro usuario -> 404 (no se filtra su existencia)."""
    from fastapi import HTTPException

    opportunity = _make_opportunity(user_id="someone-else")
    repo = AsyncMock()
    repo.get.return_value = opportunity
    deal_service = AsyncMock()

    service = OpportunityIntegrationService(
        opportunity_repository=repo, deal_service=deal_service
    )
    with pytest.raises(HTTPException) as exc:
        await service.convert_to_deal(opportunity_id="opp-1", user_id="user_1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_opportunity_integration_missing_opportunity_404():
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.get.return_value = None
    deal_service = AsyncMock()

    service = OpportunityIntegrationService(
        opportunity_repository=repo, deal_service=deal_service
    )
    with pytest.raises(HTTPException) as exc:
        await service.convert_to_deal(opportunity_id="opp-missing", user_id="user_1")
    assert exc.value.status_code == 404
