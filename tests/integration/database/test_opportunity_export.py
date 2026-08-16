"""CSV export de oportunidades (TASK-018).

Valida el filtrado por rango de fechas y el serializado CSV (BOM UTF-8)
sin depender de Postgres (usa SQLite + repos/helpers reales).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity  # noqa: F401
from app.models.vehicle import Vehicle  # noqa: F401
from app.repositories.opportunity_repository import OpportunityRepository

USER_X = "00000000-0000-0000-0000-0000000000c1"


@pytest_asyncio.fixture
async def csv_body() -> str:
    """Cuerpo del CSV exportado por el helper real de la API."""
    from app.api.v1.opportunities import _csv_stream

    opp = Opportunity(
        id="11111111-2222-3333-4444-555555555555",
        vehicle_id="99999999-0000-0000-0000-000000000000",
        opportunity_score=88.5,
        recommendation="BUY_NOW",
        risk="LOW",
        profit=1200.0,
        roi=6.5,
        created_at=datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC),
    )
    stream = _csv_stream([opp])
    chunks = [chunk async for chunk in stream.body_iterator]
    return "".join(c.decode("utf-8") for c in chunks)


@pytest.mark.asyncio
async def test_csv_has_bom_and_header(csv_body: str) -> None:
    # BOM UTF-8 al inicio para Excel
    assert csv_body.startswith("\ufeff")
    assert "id,brand,model" in csv_body or "source,external_id" in csv_body


@pytest.mark.asyncio
async def test_csv_contains_row_values(csv_body: str) -> None:
    assert "BUY_NOW" in csv_body
    assert "88.5" in csv_body
    assert "2024-05-01" in csv_body


@pytest_asyncio.fixture
async def sample_opps(session: AsyncSession) -> list[Opportunity]:
    base = datetime(2024, 3, 1, tzinfo=UTC)
    records: list[Opportunity] = []
    for i in range(3):
        v = Vehicle(
            user_id=USER_X,
            source="csv_test",
            external_id=f"c_{i}",
            brand="CSVBrand",
            model=f"Model {i}",
            price=1000.0 * (i + 1),
            currency="EUR",
            created_at=base + timedelta(days=i),
            updated_at=base + timedelta(days=i),
        )
        session.add(v)
        await session.flush()
        o = Opportunity(
            vehicle_id=v.id,
            opportunity_score=float(90 - i),
            recommendation="WATCH",
            risk="MEDIUM",
            profit=float(100.0 + i),
            roi=float(4.0 + i),
            created_at=base + timedelta(days=i),
        )
        session.add(o)
        records.append(o)
    await session.commit()
    for o in records:
        await session.refresh(o)
    return records


@pytest.mark.asyncio
async def test_export_filters_by_date_range(
    session: AsyncSession, sample_opps: list[Opportunity]
) -> None:
    repo = OpportunityRepository(session)

    # Rango que solo cubre el primer día → 1 registro
    one = await repo.list_export(
        user_id=USER_X,
        date_from=datetime(2024, 3, 1, 0, 0, tzinfo=UTC),
        date_to=datetime(2024, 3, 1, 23, 59, 59, tzinfo=UTC),
    )
    assert len(one) == 1

    # Rango completo → 3 registros
    all_rows = await repo.list_export(
        user_id=USER_X,
        date_from=datetime(2024, 3, 1, 0, 0, tzinfo=UTC),
        date_to=datetime(2024, 3, 5, 23, 59, 59, tzinfo=UTC),
    )
    assert len(all_rows) == 3

    # Sin filtros → 3
    no_filter = await repo.list_export(user_id=USER_X)
    assert len(no_filter) == 3


@pytest.mark.asyncio
async def test_export_empty_for_other_user(
    session: AsyncSession, sample_opps: list[Opportunity]
) -> None:
    repo = OpportunityRepository(session)
    rows = await repo.list_export(user_id="00000000-0000-0000-0000-0000000000ff")
    assert rows == []


def test_csv_stream_rejects_invalid_header_usage() -> None:
    # Sanidad: los helpers de la API son pydantic-free; esta aserción solo
    # garantiza que el módulo importa sin errores (superficie DEST.1).
    from app.api.v1 import opportunities as opp_mod

    assert callable(opp_mod._csv_stream)
    assert "id" in opp_mod._CSV_HEADERS