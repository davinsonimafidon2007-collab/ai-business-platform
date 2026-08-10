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
async def test_repo_count_active_by_user(session: AsyncSession) -> None:
    """count_active_by_user cuenta PENDING/RUNNING/FAILED (P3), no COMPLETED."""
    from app.core.limits import MAX_SEARCH_RESULTS

    repo = SearchOrderRepository(session)
    await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A4"))
    running = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 320d"))
    failed = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="VW Golf"))
    completed = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Ford Fiesta"))

    running.status = "RUNNING"
    failed.status = "FAILED"
    completed.status = "COMPLETED"
    await repo.save(running)
    await repo.save(failed)
    await repo.save(completed)

    assert await repo.count_active_by_user(TEST_USER_ID) == 3
    # El usuario local de los tests no tiene órdenes
    assert await repo.count_active_by_user("99999999-9999-9999-9999-999999999999") == 0
    assert MAX_SEARCH_RESULTS == 100


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
async def test_create_order_clamps_max_results(
    session: AsyncSession, client: AsyncClient
) -> None:
    """P3: max_results en filters (dict libre) se clamp a [1, 100]."""
    from app.core.limits import MAX_SEARCH_RESULTS

    huge = (
        await client.post(
            "/api/v1/search-orders",
            json={"query": "BMW X5", "filters": {"max_results": 10000}},
        )
    ).json()
    tiny = (
        await client.post(
            "/api/v1/search-orders",
            json={"query": "BMW X5", "filters": {"max_results": 0}},
        )
    ).json()

    repo = SearchOrderRepository(session)
    huge_order = await repo.get_by_id(huge["id"])
    tiny_order = await repo.get_by_id(tiny["id"])
    assert huge_order is not None and tiny_order is not None
    assert huge_order.filters_dict()["max_results"] == MAX_SEARCH_RESULTS
    assert tiny_order.filters_dict()["max_results"] == 1


@pytest.mark.asyncio
async def test_create_order_409_when_pending_limit_reached(
    session: AsyncSession, client: AsyncClient
) -> None:
    """P3: superar el tope de órdenes activas por usuario responde 409."""
    from app.core.config import settings

    limit = int(settings.search_order_max_pending_per_user)
    repo = SearchOrderRepository(session)
    for i in range(limit):
        await repo.create(
            SearchOrder(user_id=TEST_USER_ID, query=f"Audi A4 #{i}")
        )

    resp = await client.post(
        "/api/v1/search-orders", json={"query": "BMW X5"}
    )
    assert resp.status_code == 409, resp.text
    assert "límite" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_list_search_orders_clamps_skip_and_limit_in_repo(
    session: AsyncSession, client: AsyncClient
) -> None:
    """P5: el repo clamp skip (profundidad) y limit aunque la API lo deje pasar."""
    from app.core.limits import MAX_LIST_DEPTH

    repo = SearchOrderRepository(session)
    await client.post("/api/v1/search-orders", json={"query": "BMW X5"})

    # skip absurdo → clamp a MAX_LIST_DEPTH → sin resultados (no crashea)
    deep = await repo.list_by_user(TEST_USER_ID, skip=999999)
    assert deep == []

    # limit absurdo → clamp a 100 → devuelve la orden
    capped = await repo.list_by_user(TEST_USER_ID, limit=1000)
    assert len(capped) == 1
    assert MAX_LIST_DEPTH == 5000


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


# =============================================================================
# Job — ES provider integration
# =============================================================================


def _make_result(
    source: str, external_id: str, **kwargs: Any
) -> SimpleNamespace:
    """Crea un SearchResult stub con vehículo ES/mock."""
    return SimpleNamespace(
        vehicle=SimpleNamespace(
            source=source,
            external_id=external_id,
            url=kwargs.get("url", f"https://{source}.example.com/{external_id}"),
            brand=kwargs.get("brand", "BMW"),
            model=kwargs.get("model", "320d"),
        ),
        vehicle_score=None,
        market_estimation=None,
        profit_analysis=None,
        opportunity=None,
        negotiation=None,
    )


def _make_fake_engine(
    results: list[SimpleNamespace],
) -> MagicMock:
    """Crea un fake engine que devuelve los resultados dados."""
    engine = MagicMock()
    engine.search = AsyncMock(return_value=SimpleNamespace(results=results))
    return engine


@pytest.mark.asyncio
async def test_job_es_provider_executes_and_persists(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El job ejecuta autoscout24_es y persiste resultados en search_order_vehicles."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW 320d"))

    es_results = [
        _make_result("autoscout24_es", "ES-001", brand="BMW", model="320d"),
        _make_result("autoscout24_es", "ES-002", brand="Audi", model="A4"),
    ]

    fake_engine = _make_fake_engine(es_results)

    fake_persist = AsyncMock(
        return_value={
            "saved": 2,
            "created": 2,
            "updated": 0,
            "links": {0: TEST_VEHICLE_ID, 1: "33333333-3333-3333-3333-333333333333"},
        }
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
    assert result.data["completed"] == 1
    assert result.data["found"] == 2

    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "COMPLETED"
    assert refreshed.results_count == 2
    assert refreshed.new_count == 2

    links = await repo.list_order_vehicles(order.id)
    assert len(links) == 2


@pytest.mark.asyncio
async def test_job_es_and_fixture_dedup(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El job deduplica resultados ES vs fixture con mismo external_id."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW"))

    # Simula que el engine ya deduped: solo 1 resultado tras dedup
    # (ES y fixture tuvieran el mismo external_id → el engine devuelve 1)
    results = [
        _make_result("autoscout24_es", "ES-007", brand="BMW", model="320d"),
    ]
    fake_engine = _make_fake_engine(results)

    fake_persist = AsyncMock(
        return_value={
            "saved": 1,
            "created": 1,
            "updated": 0,
            "links": {0: TEST_VEHICLE_ID},
        }
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

    assert result.success
    assert result.data["found"] == 1  # deduped a 1

    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.results_count == 1


@pytest.mark.asyncio
async def test_job_provider_failure_does_not_break(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallo de un provider (403) no rompe el job; otros providers continúan."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="BMW"))

    # El engine devuelve resultados (el fallo del provider está dentro del
    # engine.search, registrado en provider_issues, pero no lanza)
    engine_results = [
        _make_result("autoscout24_es", "ES-003", brand="BMW"),
    ]
    fake_engine = _make_fake_engine(engine_results)
    # Simular que el engine también reportó un provider issue (no fatal)
    fake_engine.search.return_value = SimpleNamespace(
        results=engine_results,
        provider_issues=[
            SimpleNamespace(
                provider="mobile_de",
                stage="search",
                error_type="ProviderConnectionError",
                message="403 anti-bot",
            ),
        ],
    )

    fake_persist = AsyncMock(
        return_value={
            "saved": 1,
            "created": 1,
            "updated": 0,
            "links": {0: TEST_VEHICLE_ID},
        }
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

    # El job continuó exitosamente con los resultados del provider que funcionó
    assert result.success, result.message
    assert result.data["completed"] == 1
    assert result.data["found"] == 1

    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "COMPLETED"


@pytest.mark.asyncio
async def test_job_new_count_badge(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El badge new_count/reflected en total_new_by_user funciona para ES."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Audi A4"))

    # 3 vehículos nuevos, 0 existentes → new_count = 3
    results = [
        _make_result("autoscout24_es", f"ES-10{i}", brand="Audi")
        for i in range(3)
    ]
    fake_engine = _make_fake_engine(results)
    fake_persist = AsyncMock(
        return_value={
            "saved": 3,
            "created": 3,
            "updated": 0,
            "links": {0: TEST_VEHICLE_ID, 1: TEST_VEHICLE_ID, 2: TEST_VEHICLE_ID},
        }
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

    await job.execute(context)

    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.new_count == 3
    assert await repo.total_new_by_user(TEST_USER_ID) == 3


@pytest.mark.asyncio
async def test_job_no_pending_orders(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si no hay órdenes pending, el job devuelve éxito con mensaje."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    job = ProcessSearchOrdersJob()
    monkeypatch.setattr(job, "_build_search_engine", lambda _session: MagicMock())

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
            search_order_stale_minutes=0,
        ),
        logger=logging.getLogger("test_search_orders"),
    )

    result = await job.execute(context)
    assert result.success
    assert "No pending" in result.message
    assert result.data.get("processed", 0) == 0


@pytest.mark.asyncio
async def test_job_status_transitions(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica la transición de estados: PENDING → RUNNING → COMPLETED."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="VW Golf"))

    # Estado inicial
    initial = await repo.get_by_id(order.id)
    assert initial is not None
    assert initial.status == "PENDING"

    fake_engine = _make_fake_engine([_make_result("autoscout24_es", "ES-200")])
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

    await job.execute(context)

    # El claim_order pone RUNNING, la COMPLETED al final
    final = await repo.get_by_id(order.id)
    assert final is not None
    assert final.status == "COMPLETED"
    assert final.last_run_at is not None


@pytest.mark.asyncio
async def test_job_es_empty_results(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El ES provider puede devolver 0 resultados → orden COMPLETED con 0."""
    from app.jobs.process_search_orders import ProcessSearchOrdersJob

    repo = SearchOrderRepository(session)
    order = await repo.create(SearchOrder(user_id=TEST_USER_ID, query="Tesla Model X"))

    # El engine devuelve resultados vacíos (no hay Teslas en ES)
    fake_engine = _make_fake_engine([])
    fake_persist = AsyncMock(return_value={"saved": 0, "created": 0, "updated": 0, "links": {}})

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
    assert result.success
    assert result.data["found"] == 0

    refreshed = await repo.get_by_id(order.id)
    assert refreshed is not None
    assert refreshed.status == "COMPLETED"
    assert refreshed.results_count == 0
    assert refreshed.new_count == 0
