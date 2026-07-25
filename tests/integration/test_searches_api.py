from __future__ import annotations

from fastapi import status
from httpx import AsyncClient, ASGITransport
import pytest

from app.main import app
from app.db.session import get_db_session
from app.models.base import Base


@pytest.fixture
def db_session():
    """Override the get_db_session dependency for testing."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    async def _get_session():
        async with session_factory() as session:
            yield session

    return _get_session


@pytest.fixture
def client(db_session):
    """Create a test client with the in-memory database."""
    app.dependency_overrides[get_db_session] = db_session
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_create_search(client: AsyncClient) -> None:
    payload = {
        "name": "BMW X5 en Alemania",
        "country": "DE",
        "brands": "BMW",
        "models": "X5",
        "filters": '{"year_min": 2018, "price_max": 50000}',
    }
    response = await client.post("/searches", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "BMW X5 en Alemania"
    assert data["country"] == "DE"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_searches(client: AsyncClient) -> None:
    await client.post("/searches", json={"name": "Search 1", "country": "DE"})
    await client.post("/searches", json={"name": "Search 2", "country": "ES"})

    response = await client.get("/searches")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_search_not_found(client: AsyncClient) -> None:
    response = await client.get("/searches/non-existent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_search(client: AsyncClient) -> None:
    create_resp = await client.post("/searches", json={"name": "Original", "country": "DE"})
    search_id = create_resp.json()["id"]

    response = await client.patch(f"/searches/{search_id}", json={"name": "Updated"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_search(client: AsyncClient) -> None:
    create_resp = await client.post("/searches", json={"name": "To Delete", "country": "DE"})
    search_id = create_resp.json()["id"]

    response = await client.delete(f"/searches/{search_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT