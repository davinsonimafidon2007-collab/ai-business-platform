"""Integration tests for the inspection vision analysis API endpoint.

POST /api/v1/inspections/{id}/analyze

These tests validate the HTTP layer, request/response serialisation,
and error handling. No real vision provider is used — the service is
mocked through dependency overrides.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.v1.dependencies import get_inspection_service
from app.api.v1.routes.inspection import router
from app.dependencies.auth import get_current_user
from app.models.user import User

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


def _owned_session(session_id: str) -> SimpleNamespace | None:
    """Devuelve una sesión que pertenece al TEST_USER_ID."""
    if session_id == "invalid":
        return None
    return SimpleNamespace(user_id=TEST_USER_ID)


@pytest.fixture
def service() -> AsyncMock:
    service = AsyncMock()
    service.get_session = AsyncMock(side_effect=_owned_session)
    return service


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

    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


# =============================================================================
# Tests
# =============================================================================


class TestAnalyzePhotosEndpoint:

    def test_analyze_photos_returns_200(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """POST /inspections/{id}/analyze debe devolver 200 OK."""
        service.analyze_photos = AsyncMock(
            return_value={
                "summary": "Sugerencias generadas.",
                "suggestions": [
                    {
                        "photo_id": "photo-1",
                        "observation_id": "obs-1",
                        "category_id": "exterior",
                        "item_id": "pintura",
                        "status": "WARNING",
                        "severity": "MEDIUM",
                        "confidence": "MEDIUM",
                        "notes": "Posible rayón.",
                        "suggested_repair_cost": 150.0,
                    },
                ],
            }
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={"photo_ids": None},
        )
        assert response.status_code == 200

    def test_analyze_photos_returns_json(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """La respuesta debe ser JSON."""
        service.analyze_photos = AsyncMock(
            return_value={"summary": "", "suggestions": []}
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={},
        )
        assert response.headers["content-type"] == "application/json"

    def test_analyze_photos_response_structure(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """La respuesta debe contener summary y suggestions."""
        service.analyze_photos = AsyncMock(
            return_value={
                "summary": "Análisis completado.",
                "suggestions": [
                    {
                        "photo_id": "photo-1",
                        "observation_id": "obs-1",
                        "category_id": "exterior",
                        "item_id": "pintura",
                        "status": "WARNING",
                        "severity": "MEDIUM",
                        "confidence": "MEDIUM",
                        "notes": "Rayón detectado.",
                        "suggested_repair_cost": 150.0,
                    },
                ],
            }
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={},
        )
        data = response.json()
        assert "summary" in data
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_analyze_photos_suggestion_fields(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """Cada sugerencia debe tener todos los campos esperados."""
        service.analyze_photos = AsyncMock(
            return_value={
                "summary": "Test",
                "suggestions": [
                    {
                        "photo_id": "photo-1",
                        "observation_id": "obs-1",
                        "category_id": "exterior",
                        "item_id": "pintura",
                        "status": "WARNING",
                        "severity": "MEDIUM",
                        "confidence": "MEDIUM",
                        "notes": "Defecto visual.",
                        "suggested_repair_cost": 200.0,
                    },
                ],
            }
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={},
        )
        data = response.json()
        suggestion = data["suggestions"][0]
        assert suggestion["photo_id"] == "photo-1"
        assert suggestion["observation_id"] == "obs-1"
        assert suggestion["category_id"] == "exterior"
        assert suggestion["item_id"] == "pintura"
        assert suggestion["status"] == "WARNING"
        assert suggestion["severity"] == "MEDIUM"
        assert suggestion["confidence"] == "MEDIUM"
        assert suggestion["notes"] == "Defecto visual."
        assert suggestion["suggested_repair_cost"] == 200.0

    def test_analyze_photos_with_photo_ids_filter(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """Enviar photo_ids debe filtrar las fotos a analizar."""
        service.analyze_photos = AsyncMock(
            return_value={"summary": "Filtered analysis", "suggestions": []}
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={"photo_ids": ["photo-1"]},
        )
        assert response.status_code == 200
        service.analyze_photos.assert_called_with("session-1", ["photo-1"])

    def test_analyze_photos_empty_photo_ids(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """photo_ids: null debe analizar todas las fotos."""
        service.analyze_photos = AsyncMock(
            return_value={"summary": "", "suggestions": []}
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={"photo_ids": None},
        )
        assert response.status_code == 200
        service.analyze_photos.assert_called_with("session-1", None)

    def test_analyze_photos_no_suggestions(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """Debe manejar correctamente una respuesta sin sugerencias."""
        service.analyze_photos = AsyncMock(
            return_value={"summary": "Sin defectos detectados.", "suggestions": []}
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={},
        )
        data = response.json()
        assert data["summary"] == "Sin defectos detectados."
        assert data["suggestions"] == []

    def test_analyze_photos_missing_session_returns_404(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """Sesión inexistente (o de otro usuario) debe devolver 404."""
        response = client.post(
            "/api/v1/inspections/invalid/analyze",
            json={},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_analyze_photos_no_vision_provider_returns_400(
        self, client: TestClient, service: AsyncMock
    ) -> None:
        """Sin proveedor de visión configurado debe devolver 400."""
        service.analyze_photos = AsyncMock(
            side_effect=ValueError("Vision provider is not configured")
        )
        response = client.post(
            "/api/v1/inspections/session-1/analyze",
            json={},
        )
        assert response.status_code == 400
        assert "not configured" in response.json()["detail"]

