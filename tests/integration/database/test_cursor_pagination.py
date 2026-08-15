"""Cursor pagination tests (TASK-019).

Valida keyset pagination en VehicleRepository.list_cursor y
OpportunityRepository.list_cursor: sin huecos/duplicados entre páginas,
total correcto y has_more/next_cursor coherentes, incluyendo created_at
repetidos (tie-break por id) y cursores corruptos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.pagination import decode_cursor, encode_cursor

USER_A = "00000000-0000-0000-0000-0000000000a1"
USER_B = "00000000-0000-0000-0000-0000000000b1"


def _vehicle(user_id: str, i: int, created_at: datetime) -> Vehicle:
    return Vehicle(
        user_id=user_id,
        source="cursor_test",
        external_id=f"veh_{i}",
        brand="Cursor",
        model=f"Model {i}",
        price=1000.0 * i,
        currency="EUR",
        created_at=created_at,
        updated_at=created_at,
    )


@pytest_asyncio.fixture
async def vehicles(session: AsyncSession) -> list[Vehicle]:
    """5 vehículos para USER_A + 1 para USER_B, created_at controlados."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    records: list[Vehicle] = []
    # created_at "repetido" a propósito en los índices 0 y 4 para probar el
    # tie-break por id.
    times = [base, base + timedelta(hours=1),
             base + timedelta(hours=2),
             base + timedelta(hours=2),
             base,]
    for i, ts in enumerate(times):
        records.append(_vehicle(USER_A, i, ts))
    records.append(_vehicle(USER_B, 99, base))
    for v in records:
        session.add(v)
    await session.commit()
    for v in records:
        await session.refresh(v)
    return records


class TestVehicleCursor:
    @pytest.mark.asyncio
    async def test_first_page_returns_expected(self, session: AsyncSession, vehicles: list[Vehicle]) -> None:
        repo = VehicleRepository(session)
        items, total, has_more, next_cursor = await repo.list_cursor(USER_A, limit=2)
        assert total == 5
        assert len(items) == 2
        assert has_more is True
        assert next_cursor is not None
        # Orden created_at DESC, id DESC
        assert items[0].created_at >= items[1].created_at

    @pytest.mark.asyncio
    async def test_walk_all_pages_no_gaps_or_dupes(self, session: AsyncSession, vehicles: list[Vehicle]) -> None:
        repo = VehicleRepository(session)
        seen: list[str] = []
        cursor: str | None = None
        pages = 0
        while True:
            items, total, has_more, next_cursor = await repo.list_cursor(USER_A, cursor=cursor, limit=2)
            assert total == 5
            seen.extend(v.id for v in items)
            pages += 1
            if not has_more:
                break
            assert next_cursor is not None
            cursor = next_cursor
        assert pages == 3
        assert len(seen) == len(set(seen)) == 5

    @pytest.mark.asyncio
    async def test_corrupt_cursor_acts_as_first_page(self, session: AsyncSession, vehicles: list[Vehicle]) -> None:
        repo = VehicleRepository(session)
        items, total, has_more, _ = await repo.list_cursor(USER_A, cursor="not-a-valid-base64!!", limit=100)
        assert total == 5
        assert len(items) == 5
        assert has_more is False

    @pytest.mark.asyncio
    async def test_scoped_to_user(self, session: AsyncSession, vehicles: list[Vehicle]) -> None:
        repo = VehicleRepository(session)
        items, total, has_more, _ = await repo.list_cursor(USER_B, limit=100)
        assert total == 1
        assert len(items) == 1
        assert items[0].external_id == "veh_99"
        assert has_more is False


class TestOpportunityCursor:
    @pytest_asyncio.fixture
    async def opportunities(self, session: AsyncSession, vehicles: list[Vehicle]) -> None:
        for i, v in enumerate(vehicles):
            session.add(
                Opportunity(
                    vehicle_id=v.id,
                    opportunity_score=float(100 - i),
                    recommendation="BUY_NOW" if i < 3 else "WATCH",
                    risk="LOW",
                    profit=float(500.0 * i),
                    roi=float(10.0 * i),
                )
            )
        await session.commit()

    @pytest.mark.asyncio
    async def test_opportunity_cursor_pages(self, session: AsyncSession, opportunities: None, vehicles: list[Vehicle]) -> None:
        repo = OpportunityRepository(session)
        items, total, has_more, next_cursor = await repo.list_cursor(
            user_id=USER_A, limit=2
        )
        assert total == 5
        assert len(items) == 2
        assert has_more is True
        assert next_cursor is not None
        assert all(o.vehicle_id is not None for o in items)

        # Recorremos todas las páginas
        seen: list[str] = []
        cursor = next_cursor
        while cursor:
            items2, total2, has_more2, next2 = await repo.list_cursor(
                user_id=USER_A, cursor=cursor, limit=2
            )
            assert total2 == 5
            seen.extend(o.id for o in items2)
            cursor = next2 if has_more2 else None
        assert len(seen) == 3  # 5 - 2 de la primera página


class TestCursorCodec:
    def test_roundtrip(self) -> None:
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        token = encode_cursor(ts, "abc-123")
        decoded_ts, decoded_id = decode_cursor(token)
        assert decoded_id == "abc-123"
        assert decoded_ts == ts

    def test_garbage_returns_none(self) -> None:
        assert decode_cursor(None) == (None, None)
        assert decode_cursor("!!!") == (None, None)
        assert decode_cursor("aGVsbG8=") == (None, None)  # "hello" no es JSON de par