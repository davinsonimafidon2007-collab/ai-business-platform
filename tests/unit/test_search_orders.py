"""Tests del sistema de órdenes de búsqueda en background (PERSONAL.NOAUTH).

Cubre:
- SearchOrderRepository: create/pending, add_vehicle idempotente,
  mark_seen + badge, total_new_by_user.
- Endpoints /api/v1/search-orders: crear (deriva max_purchase_price del
  presupuesto total), listar, detalle, new-count, marcar visto, eliminar.
- ProcessSearchOrdersJob: una orden PENDING pasa a COMPLETED con los
  vehículos nuevos contabilizados en new_count.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.jobs.base import JobContext
from app.main import app
from app.models.base import Base
from app.models.role import Role
from app.models.search_order import SearchOrder
from app.models.user import User
from app.repositories.search_order_repository import SearchOrderRepository

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_VEHICLE_ID = "22222222-2222-2222-2222-222222222222"


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# =============================================================================
# Repository
# =============================================================================


@pytest.mark.asyncio
async def test_repo_create_and_pending(session: AsyncSession) -> None:
    repo = SearchOrderRepository(session)
    saved = await repo.create(
        SearchOrder(user_id=TEST_USER_ID, query="Audi A4", filters={"max_results": 10})
    )
    assert saved.status == "PENDING"
    pending = await repo.pending_orders()
    assert [o.id for o in pending] == [saved.id]


@pytest.mark.asyncio
async def test_repo_pending_skips_failed_over_max_attempts(session: AsyncSession) -> None:
    """Una orden FAILED con attempts >= max_attempts se abandona (J1)."""
    from datetime import UTC, datetime, timedelta

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A4"))
    order.status = "FAILED"
    order.attempts = 5
    order.last_run_at = datetime.now(UTC) - timedelta(hours=1)
    await repo.save(order)

    pending = await repo.pending_orders(max_attempts=5, retry_cooldown_minutes=0)
    assert order.id not in [o.id for o in pending]


@pytest.mark.asyncio
async def test_repo_pending_failed_within_cooldown_skipped(session: AsyncSession) -> None:
    """Una orden FAILED reciente no se reintenta hasta pasada la cooldown (J1)."""
    from datetime import UTC, datetime

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A4"))
    order.status = "FAILED"
    order.attempts = 1
    order.last_run_at = datetime.now(UTC)
    await repo.save(order)

    pending = await repo.pending_orders(max_attempts=5, retry_cooldown_minutes=30)
    assert order.id not in [o.id for o in pending]


@pytest.mark.asyncio
async def test_repo_pending_failed_after_cooldown_included(session: AsyncSession) -> None:
    """Una orden FAILED antigua y con intentos restantes sí se reintenta (J1)."""
    from datetime import UTC, datetime, timedelta

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A4"))
    order.status = "FAILED"
    order.attempts = 2
    order.last_run_at = datetime.now(UTC) - timedelta(hours=2)
    await repo.save(order)

    pending = await repo.pending_orders(max_attempts=5, retry_cooldown_minutes=30)
    assert [o.id for o in pending] == [order.id]


@pytest.mark.asyncio
async def test_persist_returns_links(session: AsyncSession) -> None:
    """persist_engine_result devuelve vehicle_id por índice para vincular (J3)."""
    from app.services.search_persistence import SearchPersistenceService

    svc = SearchPersistenceService(session)
    result = SimpleNamespace(
        results=[
            SimpleNamespace(
                vehicle=SimpleNamespace(
                    source="mobile_de", external_id="ext-1", brand="BMW", model="320d"
                ),
                vehicle_score=None,
                market_estimation=None,
                profit_analysis=None,
                opportunity=None,
                negotiation=None,
            ),
            SimpleNamespace(
                vehicle=SimpleNamespace(source="", external_id=None),
                vehicle_score=None,
                market_estimation=None,
                profit_analysis=None,
                opportunity=None,
                negotiation=None,
            ),
        ]
    )
    info = await svc.persist_engine_result(user_id=TEST_USER_ID, engine_result=result)

    assert 0 in info["links"]
    assert 1 not in info["links"]
    assert info["saved"] == 1


@pytest.mark.asyncio
async def test_job_increments_attempts_on_failure(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un fallo del job marca FAILED e incrementa attempts (J1)."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 320d"))

    async def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("provider 403")

    fake_engine = MagicMock()
    fake_engine.search = AsyncMock(side_effect=_boom)

    job = ProcessSearchOrdersJob()
    monkeypatch.setattr(
        "app.jobs.process_search_orders.SearchPersistenceService",
        lambda _session: MagicMock(),
    )
    monkeypatch.setattr(job, "_build_search_engine", lambda _session: fake_engine)

    db_manager = MagicMock()

    class _Ctx:
        def __init__(self, s: AsyncSession) -> None:
            self._s = s

        async def __aenter__(self) -> AsyncSession:
            return self._s

        async def __aexit__(self, *_: Any) -> None:
            return None

    db_manager.get_session.return_value = _Ctx(session)
    context = JobContext(
        db_manager=db_manager,
        settings=MagicMock(
            search_orders_per_run=5,
            search_order_max_attempts=5,
            search_order_retry_cooldown_minutes=30,
            search_order_stale_minutes=15,
        ),
        logger=logging.getLogger("test_search_orders"),
    )

    result = await job.execute(context)
    assert result.success is False, result.message
    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert refreshed.attempts == 1


@pytest.mark.asyncio
async def test_repo_add_vehicle_idempotent(session: AsyncSession) -> None:
    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 320d"))
    link1 = await repo.add_vehicle(order, TEST_VEHICLE_ID, result_json='{"a":1}')
    link2 = await repo.add_vehicle(order, TEST_VEHICLE_ID, result_json='{"a":2}')
    assert link1.id == link2.id
    links = await repo.list_order_vehicles(order.id)
    assert len(links) == 1
    assert links[0].result_json == '{"a":2}'


@pytest.mark.asyncio
async def test_repo_mark_seen_resets_badge(session: AsyncSession) -> None:
    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="VW Golf"))
    await repo.add_vehicle(order, TEST_VEHICLE_ID)
    order.results_count = 1
    order.new_count = 1
    await repo.save(order)

    assert await repo.total_new_by_user(TEST_USER_ID) == 1

    await repo.mark_seen(order.id, TEST_USER_ID)

    assert order.new_count == 0
    assert await repo.total_new_by_user(TEST_USER_ID) == 0
    links = await repo.list_order_vehicles(order.id)
    assert all(link.seen for link in links)


@pytest.mark.asyncio
async def test_repo_stale_running_recovery(session: AsyncSession) -> None:
    """Una orden RUNNING huérfana (crash) se detecta y reencola a PENDING."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A3"))
    # save() sobrescribe updated_at a now; simulamos el crash con UPDATE directo
    await session.execute(
        update(SearchOrder)
        .where(SearchOrder.id == order.id)
        .values(
            status="RUNNING",
            updated_at=datetime.now(UTC) - timedelta(minutes=60),
        )
    )
    await session.commit()

    stale = await repo.stale_running_orders(stale_minutes=15)
    assert [o.id for o in stale] == [order.id]

    await repo.reset_to_pending(stale[0])
    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "PENDING"


@pytest.mark.asyncio
async def test_repo_claim_order_atomic(session: AsyncSession) -> None:
    """El claim atómico evita que dos instancias procesen la misma orden."""
    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 1"))
    order.status = "RUNNING"
    await repo.save(order)

    # Ya está RUNNING → no se puede reclamar
    assert await repo.claim_order(order) is False

    # Al reencolar a PENDING sí se puede reclamar una vez
    order.status = "PENDING"
    await repo.save(order)
    assert await repo.claim_order(order) is True
    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "RUNNING"

    # Segundo claim falla (ya RUNNING)
    assert await repo.claim_order(order) is False


# =============================================================================
# API
# =============================================================================


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


@pytest.mark.asyncio
async def test_create_order_derives_max_purchase_price(
    session: AsyncSession, client: AsyncClient
) -> None:
    resp = await client.post(
        "/api/v1/search-orders",
        json={
            "query": "Audi A4",
            "total_budget": 12000,
            "profit_margin_min": 500,
            "profile": "SPAIN",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["total_budget"] == 12000
    assert data["max_purchase_price"] is not None
    assert data["max_purchase_price"] > 0

    order = await SearchOrderRepository(session).get_by_id(data["id"])
    assert order is not None
    assert order.max_purchase_price == data["max_purchase_price"]


@pytest.mark.asyncio
async def test_create_order_rejects_unknown_profile(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/search-orders",
        json={"query": "Audi A4", "total_budget": 12000, "profile": "MARTE"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_create_order_rejects_budget_below_fixed_costs(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/search-orders",
        json={"query": "Audi A4", "total_budget": 1500, "profile": "SPAIN"},
    )
    assert resp.status_code == 400, resp.text
    assert "Presupuesto insuficiente" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_new_count_and_list_and_detail(
    session: AsyncSession, client: AsyncClient
) -> None:
    assert (await client.get("/api/v1/search-orders/new-count")).json() == {
        "new_count": 0
    }

    created = (
        await client.post("/api/v1/search-orders", json={"query": "BMW X5"})
    ).json()

    listing = await client.get("/api/v1/search-orders")
    assert listing.status_code == 200
    assert [o["id"] for o in listing.json()] == [created["id"]]

    detail = await client.get(f"/api/v1/search-orders/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["vehicles"] == []


@pytest.mark.asyncio
async def test_mark_seen_and_delete(session: AsyncSession, client: AsyncClient) -> None:
    created = (
        await client.post("/api/v1/search-orders", json={"query": "Ford Focus"})
    ).json()

    repo = SearchOrderRepository(session)
    order = await repo.get_by_id(created["id"])
    assert order is not None
    order.new_count = 3
    await repo.save(order)

    mark = await client.post(f"/api/v1/search-orders/{created['id']}/seen")
    assert mark.status_code == 200
    assert mark.json()["new_count"] == 0

    missing = await client.get(f"/api/v1/search-orders/{created['id']}")
    assert missing.status_code == 200

    deleted = await client.delete(f"/api/v1/search-orders/{created['id']}")
    assert deleted.status_code == 204

    gone = await client.get(f"/api/v1/search-orders/{created['id']}")
    assert gone.status_code == 404


# =============================================================================
# Job
# =============================================================================


@pytest.mark.asyncio
async def test_job_completes_pending_order(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 320d"))

    fake_result = SimpleNamespace(
        vehicle=SimpleNamespace(source="mobile_de", external_id="ext-1")
    )
    fake_engine = MagicMock()
    fake_engine.search = AsyncMock(return_value=SimpleNamespace(results=[fake_result]))

    fake_persist = AsyncMock(
        return_value={"saved": 1, "created": 1, "updated": 0, "links": {0: TEST_VEHICLE_ID}}
    )

    job = ProcessSearchOrdersJob()
    monkeypatch.setattr(
        "app.jobs.process_search_orders.SearchPersistenceService",
        lambda _session: MagicMock(persist_engine_result=fake_persist),
    )
    monkeypatch.setattr(job, "_build_search_engine", lambda _session: fake_engine)
    monkeypatch.setattr(job, "_snapshot_item", staticmethod(lambda _r: "{}"))

    db_manager = MagicMock()

    class _Ctx:
        def __init__(self, s: AsyncSession) -> None:
            self._s = s

        async def __aenter__(self) -> AsyncSession:
            return self._s

        async def __aexit__(self, *_: Any) -> None:
            return None

    db_manager.get_session.return_value = _Ctx(session)
    context = JobContext(
        db_manager=db_manager,
        settings=MagicMock(
            search_orders_per_run=5,
            search_order_max_attempts=5,
            search_order_retry_cooldown_minutes=30,
            search_order_stale_minutes=15,
        ),
        logger=logging.getLogger("test_search_orders"),
    )

    result = await job.execute(context)

    assert result.success, result.message
    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "COMPLETED"
    assert refreshed.results_count == 1
    assert refreshed.new_count == 1
    links = await repo.list_order_vehicles(order.id)
    assert len(links) == 1
    assert links[0].vehicle_id == TEST_VEHICLE_ID
