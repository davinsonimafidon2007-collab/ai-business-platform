from __future__ import annotations

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.base import Base
from app.models.user import User


@pytest.fixture
def db_session():
    """Override the get_db_session dependency for testing."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
    """Create a test client with the in-memory database and mocked auth."""
    app.dependency_overrides[get_db_session] = db_session

    async def override_get_current_user() -> User:
        return User(
            id="22222222-2222-2222-2222-222222222222",
            email="search@example.com",
            hashed_password="not-used-in-override",
        )

    app.dependency_overrides[get_current_user] = override_get_current_user
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_search(client: AsyncClient) -> None:
    payload = {
        "name": "BMW X5 en Alemania",
        "country": "DE",
        "brands": "BMW",
        "models": "X5",
        "filters": '{"year_min": 2018, "price_max": 50000}',
    }
    response = await client.post("/api/v1/searches", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "BMW X5 en Alemania"
    assert data["country"] == "DE"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_searches(client: AsyncClient) -> None:
    await client.post("/api/v1/searches", json={"name": "Search 1", "country": "DE"})
    await client.post("/api/v1/searches", json={"name": "Search 2", "country": "ES"})

    response = await client.get("/api/v1/searches")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_search_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/searches/non-existent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_search(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/searches", json={"name": "Original", "country": "DE"})
    search_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/searches/{search_id}", json={"name": "Updated"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_search(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/searches", json={"name": "To Delete", "country": "DE"})
    search_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/searches/{search_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT