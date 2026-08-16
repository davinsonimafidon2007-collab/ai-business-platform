"""HTTP integration tests for the inspection API routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_inspection_service
from app.api.v1.routes.inspection import get_vehicle_repository, router
from app.dependencies.auth import get_current_user
from app.models.inspection import InspectionObservation, InspectionPhoto, InspectionSession
from app.models.user import User

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(service: AsyncMock) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_inspection_service] = lambda: service

    async def override_get_current_user() -> User:
        return User(
            id=TEST_USER_ID,
            email="test@example.com",
            hashed_password="not-used-in-override",
        )

    async def override_get_vehicle_repository() -> AsyncMock:
        repo = AsyncMock()
        repo.get_by_id.return_value = SimpleNamespace(
            id="00000000-0000-0000-0000-000000000001",
            user_id=TEST_USER_ID,
        )
        return repo

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_vehicle_repository] = override_get_vehicle_repository
    return TestClient(app)


def test_create_and_get_session(client: TestClient, service: AsyncMock) -> None:
    session = InspectionSession(
        vehicle_id="00000000-0000-0000-0000-000000000001",
        user_id=TEST_USER_ID,
    )
    service.create_session.return_value = session
    service.get_session.return_value = session
    response = client.post("/api/v1/inspections", json={"vehicle_id": session.vehicle_id})
    assert response.status_code == 201
    service.get_session_with_details.return_value = {"session": session.to_dict(), "observations": [], "photos": [], "catalog": []}
    assert client.get(f"/api/v1/inspections/{session.id}").status_code == 200
    service.get_session_with_details.return_value = None
    assert client.get("/api/v1/inspections/missing").status_code == 404


def test_update_photo_finalize_and_summary(client: TestClient, service: AsyncMock) -> None:
    session = InspectionSession(
        vehicle_id="00000000-0000-0000-0000-000000000001",
        user_id=TEST_USER_ID,
    )
    observation = InspectionObservation(session_id=session.id, category_id="exterior", item_id="pintura", status="BAD", severity="MEDIUM")
    photo = InspectionPhoto(session_id=session.id, observation_id=observation.id, file_path="/photo.jpg")
    service.update_item.return_value = observation
    service.upload_photo.return_value = photo
    service.finalize_session.return_value = session
    service.get_session.return_value = session
    assert client.put(f"/api/v1/inspections/{session.id}/items", json={"category_id": "exterior", "item_id": "pintura", "status": "BAD"}).status_code == 200
    assert client.post(f"/api/v1/inspections/{session.id}/photos", json={"observation_id": observation.id, "file_path": photo.file_path}).status_code == 201
    assert client.post(f"/api/v1/inspections/{session.id}/finalize").status_code == 200
    service.generate_summary.return_value = {"session_id": session.id, "vehicle_id": session.vehicle_id, "status": "DRAFT"}
    assert client.get(f"/api/v1/inspections/{session.id}/summary").status_code == 200
