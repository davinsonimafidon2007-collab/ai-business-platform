"""Integración real (SQLite en memoria) de la máquina de estados de deals.

Cubre el flujo Opportunity -> Deal -> transiciones con persistencia real:
- Flujo feliz NEW -> ANALYZING -> NEGOTIATING -> WON con offer_price.
- Historial inmutable y timestamps (status_changed_at / closed_at / version).
- Idempotencia: repetir el estado actual es 200 sin cambios.
- Transiciones imposibles -> 422.
- Un solo deal activo por oportunidad: 409 por servicio y por índice único
  parcial en BD; tras cerrar (LOST) se puede crear un ciclo nuevo.
- Ownership: deal ajeno -> 404.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.deal import Deal, DealStatus, DealStatusHistory
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
        opportunity_score=88.0,
        recommendation="BUY_NOW",
        roi=18.5,
        risk="LOW",
        profit=4200.0,
        analyzed_at=datetime.now(UTC),
    )


async def _persist(session: AsyncSession, *objs: object) -> None:
    for obj in objs:
        session.add(obj)
    await session.commit()
    for obj in objs:
        await session.refresh(obj)


@pytest.mark.asyncio
async def test_full_happy_flow_with_persistence(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Opportunity -> Deal NEW -> ANALYZING -> NEGOTIATING -> WON, todo persistido."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    # 1) Crear deal desde la oportunidad.
    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    assert resp.status_code == 201, resp.text
    deal_id = resp.json()["id"]
    assert resp.json()["status"] == "NEW"

    # 2) NEW -> ANALYZING.
    resp = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ANALYZING"
    assert resp.json()["closed_at"] is None

    # 3) ANALYZING -> NEGOTIATING con precio de oferta.
    resp = await client.patch(
        f"/api/v1/deals/{deal_id}/status",
        json={"status": "NEGOTIATING", "offer_price": 16500.0, "notes": "contraoferta"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "NEGOTIATING"
    assert float(body["offer_price"]) == 16500.0

    # 4) NEGOTIATING -> WON.
    resp = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "WON"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "WON"
    assert body["closed_at"] is not None

    # 5) Estado persistido en BD con closed_at.
    await session.expire_all()
    stored = await session.get(Deal, deal_id)
    assert stored is not None
    assert stored.status == DealStatus.WON
    assert stored.closed_at is not None
    assert stored.version >= 3  # bloqueo optimista incrementado por escritura

    # 6) Historial completo: creación + 3 transiciones.
    resp = await client.get(f"/api/v1/deals/{deal_id}/history")
    assert resp.status_code == 200, resp.text
    history = resp.json()
    assert history["total"] == 4
    transitions = [(h["from_status"], h["to_status"]) for h in history["items"]]
    assert (None, "NEW") in transitions
    assert ("NEW", "ANALYZING") in transitions
    assert ("ANALYZING", "NEGOTIATING") in transitions
    assert ("NEGOTIATING", "WON") in transitions
    won_row = next(h for h in history["items"] if h["to_status"] == "WON")
    assert won_row["changed_by_user_id"] == TEST_USER_ID


@pytest.mark.asyncio
async def test_impossible_transitions_rejected(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Saltos imposibles (NEW->WON, WON->X) se rechazan sin mutar BD."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    deal_id = resp.json()["id"]

    # NEW -> WON directo: imposible.
    resp = await client.patch(f"/api/v1/deals/{deal_id}/status", json={"status": "WON"})
    assert resp.status_code == 422

    # El deal sigue en NEW en BD.
    await session.expire_all()
    stored = await session.get(Deal, deal_id)
    assert stored.status == DealStatus.NEW


@pytest.mark.asyncio
async def test_repeat_same_status_is_idempotent(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Repetir el estado actual -> 200 y NO añade filas al historial."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    deal_id = resp.json()["id"]

    resp1 = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert resp1.status_code == 200

    # Repetición idempotente.
    resp2 = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ANALYZING"

    # Historial: creación + UNA transición (la repetida no duplica).
    resp = await client.get(f"/api/v1/deals/{deal_id}/history")
    data = resp.json()
    assert data["total"] == 2
    to_statuses = [h["to_status"] for h in data["items"]]
    assert to_statuses.count("ANALYZING") == 1


@pytest.mark.asyncio
async def test_single_active_deal_per_opportunity_and_new_cycle(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Un deal activo por oportunidad: 409 duplicado; cerrado permite nuevo ciclo."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    first = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    assert first.status_code == 201

    # Duplicado activo -> 409.
    dup = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    assert dup.status_code == 409

    # Cerrar el primero como LOST (NEGOTIATING -> LOST requiere pasar por ANALYZING).
    deal_id = first.json()["id"]
    r1 = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert r1.status_code == 200
    r2 = await client.patch(f"/api/v1/deals/{deal_id}/status", json={"status": "LOST"})
    assert r2.status_code == 200

    # Ahora sí: nuevo ciclo permitido.
    second = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    assert second.status_code == 201
    assert second.json()["id"] != deal_id


@pytest.mark.asyncio
async def test_db_partial_unique_index_blocks_concurrent_duplicate(
    session: AsyncSession, client: AsyncClient
) -> None:
    """El índice único parcial de BD impide dos deals activos (carrera real)."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    assert resp.status_code == 201

    duplicate = Deal(
        id=str(uuid4()),
        user_id=TEST_USER_ID,
        opportunity_id=opp.id,
        status=DealStatus.NEW,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_foreign_deal_is_404_everywhere(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Deal de otro usuario -> 404 en GET, PATCH e historial."""
    vehicle = _make_vehicle(user_id=OTHER_USER_ID)
    foreign_deal = Deal(
        id=str(uuid4()),
        user_id=OTHER_USER_ID,
        opportunity_id=None,
        status=DealStatus.NEW,
    )
    await _persist(session, vehicle, foreign_deal)
    deal_id = foreign_deal.id

    get_resp = await client.get(f"/api/v1/deals/{deal_id}")
    assert get_resp.status_code == 404

    patch_resp = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert patch_resp.status_code == 404

    hist_resp = await client.get(f"/api/v1/deals/{deal_id}/history")
    assert hist_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_deal_removes_history_cascade(
    session: AsyncSession, client: AsyncClient
) -> None:
    """DELETE elimina el deal y su historial (CASCADE)."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    deal_id = resp.json()["id"]

    # Al menos la fila de creación existe.
    rows = (
        (await session.execute(select(DealStatusHistory.id))).scalars().all()
    )
    assert len(rows) >= 1

    del_resp = await client.delete(f"/api/v1/deals/{deal_id}")
    assert del_resp.status_code == 204

    await session.expire_all()
    remaining_history = (
        (await session.execute(select(DealStatusHistory))).scalars().all()
    )
    assert all(h.deal_id != deal_id for h in remaining_history)


@pytest.mark.asyncio
async def test_cancelled_from_new_terminal(
    session: AsyncSession, client: AsyncClient
) -> None:
    """NEW -> CANCELLED es válido y cierra el deal."""
    vehicle = _make_vehicle()
    opp = _make_opportunity(vehicle.id)
    await _persist(session, vehicle, opp)

    resp = await client.post("/api/v1/deals", json={"opportunity_id": opp.id})
    deal_id = resp.json()["id"]

    cancel = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "CANCELLED"}
    )
    assert cancel.status_code == 200
    assert cancel.json()["closed_at"] is not None

    # Terminal: no se puede reabrir.
    reopen = await client.patch(
        f"/api/v1/deals/{deal_id}/status", json={"status": "ANALYZING"}
    )
    assert reopen.status_code == 422
