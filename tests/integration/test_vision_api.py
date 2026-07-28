from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.v1.dependencies import get_inspection_service
from app.api.v1.routes.inspection import router


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(service: AsyncMock) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_inspection_service] = lambda: service
    return TestClient(app)


def test_analyze_photos_returns_suggestions_without_persisting(client: TestClient, service: AsyncMock) -> None:
    service.analyze_photos.return_value = {
        "summary": "Mock result",
        "suggestions": [{
            "photo_id": "photo", "observation_id": "observation", "category_id": "exterior",
            "item_id": "pintura", "status": "WARNING", "severity": "MEDIUM",
            "confidence": "HIGH", "notes": "Review", "suggested_repair_cost": 150,
        }],
    }
    response = client.post("/api/v1/inspections/session/analyze", json={"photo_ids": ["photo"]})
    assert response.status_code == 200
    assert response.json()["suggestions"][0]["item_id"] == "pintura"
    service.update_item.assert_not_called()


def test_analyze_photos_reports_unavailable_provider(client: TestClient, service: AsyncMock) -> None:
    service.analyze_photos.side_effect = ValueError("Vision provider is not configured")
    response = client.post("/api/v1/inspections/session/analyze", json={})
    assert response.status_code == 400
