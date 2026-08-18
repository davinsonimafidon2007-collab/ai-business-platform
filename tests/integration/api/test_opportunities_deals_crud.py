"""Tests de integración del CRUD de oportunidades y DELETE de deals (TASK-021).

Usa sqlite en memoria (patrón de test_search_orders.py) con overrides de
``get_db_session`` y ``get_current_user``. Cubre:

- POST /api/v1/opportunities: crea con vehicle propio, 404 con vehicle ajeno.
- PATCH /api/v1/opportunities/{id}: actualiza campos analíticos, 404 ajeno.
- DELETE /api/v1/opportunities/{id}: elimina, 404 ajeno.
- DELETE /api/v1/deals/{deal_id}: elimina deal propio, 404 ajeno.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.deal import Deal, DealStatus
from app.models.opportunity import Opportunity
from app.models.role import Role
from app.models.user import User
from app.models.vehicle import Vehicle

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
OTHER_USER_ID = "99999999-9999-9999-9999-999999999999"


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def _get_session():
        yield session

    async def _get_current_user() -> User:
        return User(
            id=TEST_USER_ID,
            email="local@example.com",
            hashed_password="",
            full_name="Local Admin",
            is_active=True,
            is_verified=True,
            role=Role.ADMIN,
        )

    app.dependency_overrides[get_db_session] = _get_session
    app.dependency_overrides[get_current_user] = _get_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    if get_db_session in app.dependency_overrides:
        del app.dependency_overrides[get_db_session]
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


def _make_vehicle(user_id: str = TEST_USER_ID) -> Vehicle:
    return Vehicle(
        id=str(uuid4()),
        user_id=user_id,
        source="es_market_fixture",
        external_id=f"ext-{uuid4().hex[:8]}",
        brand="BMW",
        model="320",
        year=2019,
        price=18200.0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_opportunity(vehicle_id: str) -> Opportunity:
    return Opportunity(
        vehicle_id=vehicle_id,
        opportunity_score=42.0,
        recommendation="WATCH",
        roi=5.5,
        risk="MEDIUM",
        profit=1200.0,
        analyzed_at=datetime.now(UTC),
    )


async def _persist(
    session: AsyncSession, *objs: object
) -> None:
    for obj in objs:
        session.add(obj)
    await session.commit()
    for obj in objs:
        await session.refresh(obj)


# =============================================================================
# POST /api/v1/opportunities
# =============================================================================


@pytest.mark.asyncio
async def test_create_opportunity_with_own_vehicle(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle()
    await _persist(session, vehicle)

    resp = await client.post(
        "/api/v1/opportunities",
        json={
            "vehicle_id": vehicle.id,
            "score": 45.0,
            "estimated_profit": 1500.0,
            "roi_percentage": 8.0,
            "recommendation": "BUY_NOW",
            "risk_level": "LOW",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["score"] == 45.0
    assert data["estimated_profit"] == 1500.0
    assert data["recommendation"] == "BUY_NOW"
    assert data["risk_level"] == "LOW"
    assert data["vehicle"]["id"] == vehicle.id


@pytest.mark.asyncio
async def test_create_opportunity_404_for_foreign_vehicle(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle(user_id=OTHER_USER_ID)
    await _persist(session, vehicle)

    resp = await client.post(
        "/api/v1/opportunities",
        json={"vehicle_id": vehicle.id},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_create_opportunity_404_for_missing_vehicle(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/opportunities",
        json={"vehicle_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404, resp.text


# =============================================================================
# PATCH /api/v1/opportunities/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_update_opportunity_own(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.patch(
        f"/api/v1/opportunities/{opp.id}",
        json={"recommendation": "NEGOTIATE", "score": 60.0},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["recommendation"] == "NEGOTIATE"
    assert data["score"] == 60.0
    assert data["roi_percentage"] == 5.5  # no tocado


@pytest.mark.asyncio
async def test_update_opportunity_404_foreign(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle(user_id=OTHER_USER_ID)
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.patch(
        f"/api/v1/opportunities/{opp.id}",
        json={"score": 10.0},
    )
    assert resp.status_code == 404, resp.text


# =============================================================================
# DELETE /api/v1/opportunities/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_delete_opportunity_own(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.delete(f"/api/v1/opportunities/{opp.id}")
    assert resp.status_code == 204, resp.text

    gone = await session.get(Opportunity, opp.id)
    assert gone is None


@pytest.mark.asyncio
async def test_delete_opportunity_404_foreign(
    session: AsyncSession, client: AsyncClient
) -> None:
    vehicle = _make_vehicle(user_id=OTHER_USER_ID)
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.delete(f"/api/v1/opportunities/{opp.id}")
    assert resp.status_code == 404, resp.text


# =============================================================================
# DELETE /api/v1/deals/{deal_id}
# =============================================================================


def _make_deal(user_id: str = TEST_USER_ID) -> Deal:
    return Deal(
        id=str(uuid4()),
        user_id=user_id,
        opportunity_id=None,
        vehicle_id=None,
        status=DealStatus.NEW,
        notes="prueba",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_delete_deal_own(
    session: AsyncSession, client: AsyncClient
) -> None:
    deal = _make_deal()
    await _persist(session, deal)

    resp = await client.delete(f"/api/v1/deals/{deal.id}")
    assert resp.status_code == 204, resp.text

    gone = await session.get(Deal, deal.id)
    assert gone is None


@pytest.mark.asyncio
async def test_delete_deal_404_foreign(
    session: AsyncSession, client: AsyncClient
) -> None:
    deal = _make_deal(user_id=OTHER_USER_ID)
    await _persist(session, deal)

    resp = await client.delete(f"/api/v1/deals/{deal.id}")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_delete_deal_404_missing(
    client: AsyncClient,
) -> None:
    resp = await client.delete("/api/v1/deals/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404, resp.text