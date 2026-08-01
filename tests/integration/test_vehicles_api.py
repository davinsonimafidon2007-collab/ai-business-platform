from __future__ import annotations

from fastapi import status
from httpx import AsyncClient, ASGITransport
import pytest

from app.main import app
from app.db.session import get_db_session
from app.models.base import Base
from app.models.vehicle import Vehicle
from app.models.vehicle_evaluation import VehicleEvaluation
from app.models.search import Search


@pytest.fixture
def db_session():
    """Override the get_db_session dependency for testing."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

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
async def test_create_vehicle(client: AsyncClient) -> None:
    payload = {
        "source": "mobile.de",
        "external_id": "ext-001",
        "brand": "BMW",
        "model": "X5",
        "year": 2020,
        "mileage": 50000,
        "fuel_type": "Diesel",
        "transmission": "Automatic",
        "power_hp": 265,
        "price": 35000.0,
        "currency": "EUR",
    }
    response = await client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["source"] == "mobile.de"
    assert data["brand"] == "BMW"
    assert data["model"] == "X5"
    assert data["year"] == 2020
    assert data["price"] == 35000.0
    assert "id" in data


@pytest.mark.asyncio
async def test_list_vehicles(client: AsyncClient) -> None:
    # Create two vehicles
    await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
    })
    await client.post("/api/v1/vehicles", json={
        "source": "autoscout24", "external_id": "ext-002", "brand": "Audi", "model": "A4",
    })

    response = await client.get("/api/v1/vehicles")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_vehicle_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/vehicles/non-existent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_vehicle(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
    })
    vehicle_id = create_resp.json()["id"]

    response = await client.patch(f"/api/v1/vehicles/{vehicle_id}", json={"price": 30000.0})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["price"] == 30000.0


@pytest.mark.asyncio
async def test_delete_vehicle(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
    })
    vehicle_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/vehicles/{vehicle_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_create_vehicle_evaluation(client: AsyncClient) -> None:
    """POST /vehicles/{id}/evaluation calcula la evaluación en el servidor (sin body)."""
    create_resp = await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
        "year": 2020, "mileage": 50000, "price": 35000.0,
    })
    vehicle_id = create_resp.json()["id"]

    # El endpoint ya no acepta body: calcula todo con EvaluationEngine
    response = await client.post(f"/api/v1/vehicles/{vehicle_id}/evaluation")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    # Los valores los calcula el servidor, no el cliente
    assert "score" in data
    assert "classification" in data
    assert data["classification"] in ("verde", "amarillo", "rojo")


@pytest.mark.asyncio
async def test_get_vehicle_evaluation(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
        "year": 2020, "mileage": 50000, "price": 35000.0,
    })
    vehicle_id = create_resp.json()["id"]

    # Crear evaluación (sin body — la calcula el servidor)
    eval_resp = await client.post(f"/api/v1/vehicles/{vehicle_id}/evaluation")
    assert eval_resp.status_code == status.HTTP_201_CREATED
    created = eval_resp.json()

    response = await client.get(f"/api/v1/vehicles/{vehicle_id}/evaluation")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["score"] == created["score"]
    assert response.json()["classification"] == created["classification"]


@pytest.mark.asyncio
async def test_delete_vehicle_evaluation(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/vehicles", json={
        "source": "mobile.de", "external_id": "ext-001", "brand": "BMW", "model": "X5",
        "year": 2020, "mileage": 50000, "price": 35000.0,
    })
    vehicle_id = create_resp.json()["id"]

    # Crear evaluación (sin body — la calcula el servidor)
    eval_resp = await client.post(f"/api/v1/vehicles/{vehicle_id}/evaluation")
    assert eval_resp.status_code == status.HTTP_201_CREATED

    response = await client.delete(f"/api/v1/vehicles/{vehicle_id}/evaluation")
    assert response.status_code == status.HTTP_204_NO_CONTENT
