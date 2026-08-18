"""Tests de integración de jobs en background contra PostgreSQL real.

Requiere una base PostgreSQL disponible (marcador ``integration_db``; el
conftest de integration la salta automáticamente si no hay conexión).

A diferencia de los tests unit de jobs (que usan sqlite + mocks), estos
ejecutan ``ProcessSearchOrdersJob`` con el **persistence real** sobre la BD
de CI: el vehículo encontrado por el engine (stub) se persiste en ``vehicles``
y se vincula a la orden vía ``search_order_vehicles``. El engine de búsqueda
se mockea para no depender de la red.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.manager import DatabaseManager
from app.jobs.base import JobContext
from app.jobs.process_search_orders import ProcessSearchOrdersJob
from app.models.search_order import SearchOrder, SearchOrderVehicle
from app.models.user import User
from app.repositories.search_order_repository import SearchOrderRepository

TEST_USER_ID = "22222222-2222-2222-2222-222222222222"


@pytest_asyncio.fixture
async def db() -> DatabaseManager:
    manager = DatabaseManager(settings.database_url, echo=False)
    await manager.init()
    yield manager
    await manager.shutdown()


async def _ensure_user(session: AsyncSession) -> User:
    from sqlalchemy import select

    result = await session.execute(
        select(User).where(User.id == TEST_USER_ID)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=TEST_USER_ID,
            email="jobs-integration@example.com",
            hashed_password="x",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
    return user


def _fake_engine_result() -> SimpleNamespace:
    """Un SearchResult stub con vehículo persistible (source+external_id)."""
    vehicle = SimpleNamespace(
        source="es_market_fixture",
        external_id=f"jobs-int-{datetime.now(UTC).microsecond}",
        url="https://example.es/anuncio/jobs-int",
        brand="BMW",
        model="320",
        category=None,
        version=None,
        year=2019,
        mileage=100000,
        fuel_type="Diesel",
        transmission="Automatic",
        power_hp=None,
        displacement_cc=None,
        doors=None,
        color=None,
        emissions=None,
        location=None,
        seller_type=None,
        first_registration=None,
        price=18200.0,
        currency="EUR",
        vin=None,
        description=None,
        images=[],
        equipment=[],
    )
    return SimpleNamespace(
        vehicle=vehicle,
        vehicle_score=None,
        market_estimation=None,
        profit_analysis=None,
        opportunity=None,
        negotiation=None,
    )


@pytest.mark.integration_db
@pytest.mark.asyncio
async def test_search_order_job_persists_vehicles_on_postgres(
    db: DatabaseManager,
) -> None:
    """El job COMPLETA una orden y persiste+vincula vehículos en Postgres real."""
    async with db.get_session() as session:
        await _ensure_user(session)
        repo = SearchOrderRepository(session)
        order = await repo.create(
            SearchOrder(user_id=TEST_USER_ID, query="BMW 320", filters={"max_results": 5})
        )
        order_id = order.id

    fake_engine = MagicMock()
    fake_engine.search = AsyncMock(return_value=SimpleNamespace(results=[_fake_engine_result()]))

    job = ProcessSearchOrdersJob()

    class _Ctx:
        def __init__(self, s: AsyncSession) -> None:
            self._s = s

        async def __aenter__(self) -> AsyncSession:
            return self._s

        async def __aexit__(self, *_: object) -> None:
            return None

    async with db.get_session() as session:
        db_manager = MagicMock()
        db_manager.get_session.return_value = _Ctx(session)
        context = JobContext(
            db_manager=db_manager,
            settings=MagicMock(
                search_orders_per_run=5,
                search_order_max_attempts=5,
                search_order_retry_cooldown_minutes=30,
                search_order_stale_minutes=15,
            ),
            logger=logging.getLogger("test_jobs_integration"),
        )

        # Sustituir SOLO el engine (red); el persistence y repos son reales.
        job._build_search_engine = lambda _s: fake_engine  # type: ignore[method-assign]

        result = await job.execute(context)
        assert result.success, result.message

        refreshed = await repo.get_by_id(order_id)
        assert refreshed is not None
        assert refreshed.status == "COMPLETED"
        assert refreshed.results_count == 1
        assert refreshed.new_count == 1

        # El vehículo se persistió y se vinculó a la orden.
        links = await repo.list_order_vehicles(order_id)
        assert len(links) == 1
        linked: SearchOrderVehicle = links[0]
        assert linked.vehicle_id is not None

        # El vehículo existe de verdad en la tabla vehicles.
        from app.models.vehicle import Vehicle

        vehicle = await session.get(Vehicle, linked.vehicle_id)
        assert vehicle is not None
        assert vehicle.brand == "BMW"
        assert vehicle.user_id == TEST_USER_ID

        # Limpieza (orden + vehículo) para no contaminar la BD de CI.
        await session.delete(refreshed)
        if vehicle is not None:
            await session.delete(vehicle)
        await session.commit()