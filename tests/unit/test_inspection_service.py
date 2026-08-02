"""Tests for the inspection session service."""

from unittest.mock import AsyncMock

import pytest

from app.models.inspection import InspectionObservation, InspectionSession
from app.services.inspection_service import InspectionService


@pytest.fixture
def repos() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    return AsyncMock(), AsyncMock(), AsyncMock()


@pytest.fixture
def service(repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> InspectionService:
    return InspectionService(*repos)


@pytest.mark.asyncio
async def test_create_session_starts_as_draft(service: InspectionService, repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> None:
    created = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001")
    repos[0].create.return_value = created
    result = await service.create_session(created.vehicle_id, user_id="00000000-0000-0000-0000-000000000099")
    assert result is created
    assert repos[0].create.call_args.args[0].status == "DRAFT"
    assert repos[0].create.call_args.args[0].user_id == "00000000-0000-0000-0000-000000000099"


@pytest.mark.asyncio
async def test_update_item_creates_and_updates_observation(service: InspectionService, repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> None:
    repos[1].get_by_item.return_value = None
    repos[1].create.side_effect = lambda observation: observation
    created = await service.update_item("session", "exterior", "pintura", "BAD", "Rayon", 120)
    assert created.severity == "HIGH"
    assert created.estimated_repair_cost == 120

    repos[1].get_by_item.return_value = created
    repos[1].update.side_effect = lambda observation: observation
    updated = await service.update_item("session", "exterior", "pintura", "WARNING", "Nuevo", 50)
    assert updated is created
    assert updated.status == "WARNING"
    assert updated.notes == "Nuevo"


@pytest.mark.asyncio
async def test_update_item_rejects_unknown_catalog_item(service: InspectionService) -> None:
    with pytest.raises(ValueError, match="not found"):
        await service.update_item("session", "unknown", "unknown", "GOOD")


@pytest.mark.asyncio
async def test_session_details_include_catalog(service: InspectionService, repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> None:
    session = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001")
    observation = InspectionObservation(session_id=session.id, category_id="exterior", item_id="pintura", status="GOOD")
    repos[0].get_by_id.return_value = session
    repos[1].get_by_session.return_value = [observation]
    repos[2].get_by_session.return_value = []
    result = await service.get_session_with_details(session.id)
    assert result is not None
    assert result["observations"][0]["id"] == observation.id
    assert result["catalog"]


@pytest.mark.asyncio
async def test_finalize_session_stores_summary(service: InspectionService, repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> None:
    session = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001")
    observation = InspectionObservation(session_id=session.id, category_id="exterior", item_id="pintura", status="BAD", estimated_repair_cost=200, severity="CRITICAL")
    repos[0].get_by_id.return_value = session
    repos[1].get_by_session.return_value = [observation]
    repos[0].update.side_effect = lambda updated: updated
    result = await service.finalize_session(session.id)
    assert result.status == "COMPLETED"
    assert result.total_repair_cost == 200
    assert result.total_critical_defects == 1
    assert result.summary is not None


@pytest.mark.asyncio
async def test_finalize_rejects_missing_or_completed_session(service: InspectionService, repos: tuple[AsyncMock, AsyncMock, AsyncMock]) -> None:
    repos[0].get_by_id.return_value = None
    with pytest.raises(ValueError, match="not found"):
        await service.finalize_session("missing")
    repos[0].get_by_id.return_value = InspectionSession(vehicle_id="00000000-0000-0000-0000-000000000001", status="COMPLETED")
    with pytest.raises(ValueError, match="already completed"):
        await service.finalize_session("done")
