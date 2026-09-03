"""Tests de OpportunityPhaseService — flujo de aprobación OPP→DEAL (TEST.PHASE.1).

Cubre el hueco detectado en auditoría: el pipeline OPPORTUNITY→DEAL solo tenía
un smoke de wiring (``callable(...)``); aquí se ejecuta la lógica REAL del
servicio + repositorio contra SQLite en memoria: seeding idempotente,
transiciones por acción, 404/400 y serialización para la API.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager
from app.exceptions.base import AppError
from app.models.base import Base
from app.models.opportunity import Opportunity
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.opportunity_phase_service import OpportunityPhaseService

USER_ID = "33333333-3333-4333-8333-333333333333"
VEHICLE_ID = "34343434-3434-4343-8434-343434343434"


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    manager = DatabaseManager("sqlite+aiosqlite://", echo=False)
    async with manager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with manager.session_factory() as sess:
        yield sess
    await manager.shutdown()


@pytest_asyncio.fixture
async def opportunity(session: AsyncSession) -> Opportunity:
    user = User(id=USER_ID, email="phases@example.com", hashed_password="x")
    vehicle = Vehicle(
        id=VEHICLE_ID,
        user_id=USER_ID,
        source="test",
        external_id=f"ext-{uuid4()}",
        brand="BMW",
        model="330e",
        price=21000.0,
        currency="EUR",
    )
    opp = Opportunity(
        id=str(uuid4()),
        vehicle_id=VEHICLE_ID,
        opportunity_score=87.0,
        recommendation="BUY_NOW",
        roi=18.5,
        risk="LOW",
        profit=4200.0,
    )
    session.add_all([user, vehicle, opp])
    await session.commit()
    return opp


@pytest.mark.asyncio
async def test_seed_creates_four_default_phases_in_order(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)

    assert [p.order for p in phases] == [1, 2, 3, 4]
    assert [p.status for p in phases] == ["completed", "pending_approval", "pending", "pending"]
    assert phases[1].agent == "negotiation-engine"


@pytest.mark.asyncio
async def test_seed_is_idempotent(session: AsyncSession, opportunity: Opportunity) -> None:
    service = OpportunityPhaseService(session)
    first = await service.ensure_seeded(opportunity)
    second = await service.ensure_seeded(opportunity)

    assert len(second) == len(first) == 4
    assert {p.id for p in second} == {p.id for p in first}


@pytest.mark.asyncio
async def test_approve_completes_pending_approval_phase(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)
    offer = next(p for p in phases if p.order == 2)

    updated = await service.apply_action(opportunity, offer.id, "approve")
    assert updated.status == "completed"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_request_changes_sets_feedback_and_reopens(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)
    offer = phases[1]

    approved = await service.apply_action(opportunity, offer.id, "approve")
    changed = await service.apply_action(
        opportunity, approved.id, "request_changes", feedback="Sube la oferta un 8%"
    )

    assert changed.status == "in_progress"
    assert changed.feedback == "Sube la oferta un 8%"


@pytest.mark.asyncio
async def test_start_marks_in_progress_with_started_at(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)
    purchase = next(p for p in phases if p.order == 3)

    started = await service.apply_action(opportunity, purchase.id, "start")
    assert started.status == "in_progress"
    assert started.started_at is not None


@pytest.mark.asyncio
async def test_reject_aborts_phase(session: AsyncSession, opportunity: Opportunity) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)

    aborted = await service.apply_action(opportunity, phases[2].id, "reject")
    assert aborted.status == "aborted"


@pytest.mark.asyncio
async def test_invalid_action_returns_400(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)

    with pytest.raises((HTTPException, AppError)) as exc_info:
        await service.apply_action(opportunity, phases[0].id, "force_close")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_phase_of_other_opportunity_returns_404(
    session: AsyncSession, opportunity: Opportunity, session_factory=None
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)

    # Otra oportunidad distinta (misma sesión): sus ids no coinciden
    other = Opportunity(
        id=str(uuid4()),
        vehicle_id=VEHICLE_ID,
        opportunity_score=50.0,
    )
    session.add(other)
    await session.commit()

    with pytest.raises((HTTPException, AppError)) as exc_info:
        await service.apply_action(other, phases[0].id, "approve")
    assert exc_info.value.status_code == 404

    with pytest.raises((HTTPException, AppError)):
        await service.apply_action(opportunity, "no-existe", "approve")


@pytest.mark.asyncio
async def test_to_read_serializes_api_contract(
    session: AsyncSession, opportunity: Opportunity
) -> None:
    service = OpportunityPhaseService(session)
    phases = await service.ensure_seeded(opportunity)
    payload = OpportunityPhaseService.to_read(phases[1])

    assert set(payload.keys()) >= {
        "id",
        "opportunity_id",
        "title",
        "status",
        "agent",
        "order",
        "started_at",
        "completed_at",
        "feedback",
    }
    assert payload["opportunity_id"] == opportunity.id
    assert payload["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_list_phases_ordered(session: AsyncSession, opportunity: Opportunity) -> None:
    service = OpportunityPhaseService(session)
    await service.ensure_seeded(opportunity)

    listed = await service.list_phases(opportunity.id)
    titles = [p.title for p in listed]
    assert titles[0] == "Evaluación inicial"
    assert listed[-1].title == "Importación"
