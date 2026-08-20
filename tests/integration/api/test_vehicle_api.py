"""Integration tests for vehicle and provider endpoints.

GET /api/v1/vehicle/{provider}/{id}
GET /api/v1/providers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.main import app
from app.models.user import User
from app.providers.dto import VehicleDetail
from app.providers.registry import ProviderRegistry

client = TestClient(app)


@pytest.fixture(autouse=True)
def _override_current_user() -> None:
    async def _get_current_user() -> User:
        return User(
            id="00000000-0000-0000-0000-000000000001",
            email="test@example.com",
            hashed_password="",
            role="USER",
        )

    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def clear_and_setup_registry() -> None:
    """Limpia el registro y registra providers de prueba."""
    ProviderRegistry.clear()
    mock_mobile = MagicMock()
    mock_mobile.source_name = "mobile_de"
    mock_autoscout = MagicMock()
    mock_autoscout.source_name = "autoscout24"
    ProviderRegistry.register(mock_mobile)
    ProviderRegistry.register(mock_autoscout)


# =============================================================================
# Tests para GET /providers
# =============================================================================


class TestProvidersEndpoint:

    def test_providers_returns_200(self) -> None:
        """GET /api/v1/providers debe devolver 200 OK."""
        response = client.get("/api/v1/providers")
        assert response.status_code == 200

    def test_providers_returns_json(self) -> None:
        """La respuesta debe ser JSON."""
        response = client.get("/api/v1/providers")
        assert response.headers["content-type"] == "application/json"

    def test_providers_list_content(self) -> None:
        """Debe devolver la lista de proveedores."""
        response = client.get("/api/v1/providers")
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)
        assert "mobile_de" in data["providers"]
        assert "autoscout24" in data["providers"]

    def test_providers_empty(self) -> None:
        """Sin providers registrados, debe devolver lista vacía."""
        ProviderRegistry.clear()
        response = client.get("/api/v1/providers")
        data = response.json()
        assert data["providers"] == []


# =============================================================================
# Tests para GET /vehicle/{provider}/{id}
# =============================================================================


class TestVehicleDetailEndpoint:

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_returns_200(self, mock_registry_get) -> None:
        """GET /api/v1/vehicle/{provider}/{id} debe devolver 200 OK."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            return_value=VehicleDetail(
                source="mobile_de",
                external_id="12345",
                url="https://example.com/vehicle/12345",
                brand="BMW",
                model="320d",
                year=2020,
                mileage=50000,
                fuel_type="diesel",
                transmission="manual",
                power_hp=190,
                price=25000.0,
                currency="EUR",
                description="Good condition",
                images=["img1.jpg"],
            )
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        assert response.status_code == 200

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_returns_json(self, mock_registry_get) -> None:
        """La respuesta debe ser JSON."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            return_value=VehicleDetail(
                source="mobile_de",
                external_id="12345",
                url="https://example.com/vehicle/12345",
                brand="BMW",
                model="320d",
            )
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        assert response.headers["content-type"] == "application/json"

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_has_all_fields(self, mock_registry_get) -> None:
        """La respuesta debe contener todos los campos del vehículo."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            return_value=VehicleDetail(
                source="mobile_de",
                external_id="12345",
                url="https://example.com/vehicle/12345",
                brand="BMW",
                model="320d",
                category="Limousine",
                version="M Sport",
                year=2020,
                mileage=50000,
                fuel_type="diesel",
                transmission="manual",
                power_hp=190,
                displacement_cc=1995,
                doors=4,
                color="black",
                emissions="Euro 6",
                location="Berlin",
                seller_type="dealer",
                first_registration="2020-03",
                price=25000.0,
                currency="EUR",
                vin="WBA1234567890",
                description="Good condition",
                images=["img1.jpg", "img2.jpg"],
                equipment=["ABS", "ESP"],
            )
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        data = response.json()

        assert data["source"] == "mobile_de"
        assert data["external_id"] == "12345"
        assert data["brand"] == "BMW"
        assert data["model"] == "320d"
        assert data["year"] == 2020
        assert data["mileage"] == 50000
        assert data["fuel_type"] == "diesel"
        assert data["price"] == 25000.0
        assert data["images"] == ["img1.jpg", "img2.jpg"]
        assert data["equipment"] == ["ABS", "ESP"]

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_images_as_list(self, mock_registry_get) -> None:
        """Las imágenes deben devolverse como lista."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            return_value=VehicleDetail(
                source="mobile_de",
                external_id="12345",
                images=["img1.jpg", "img2.jpg", "img3.jpg"],
            )
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        data = response.json()
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 3

    def test_vehicle_detail_provider_not_found(self) -> None:
        """Proveedor inexistente debe devolver 404."""
        ProviderRegistry.clear()
        response = client.get("/api/v1/vehicle/nonexistent/12345")
        assert response.status_code == 404

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_not_found(self, mock_registry_get) -> None:
        """Vehículo inexistente debe devolver 404."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(return_value=None)
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/99999")
        assert response.status_code == 404

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_provider_error(self, mock_registry_get) -> None:
        """Error del proveedor debe devolver 500."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            side_effect=Exception("Connection error")
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        assert response.status_code == 500

    @patch("app.api.v1.routes.vehicles.ProviderRegistry.get")
    def test_vehicle_detail_serialization(self, mock_registry_get) -> None:
        """La respuesta debe ser JSON serializable."""
        mock_provider = AsyncMock()
        mock_provider.source_name = "mobile_de"
        mock_provider.get_vehicle = AsyncMock(
            return_value=VehicleDetail(
                source="mobile_de",
                external_id="12345",
                brand="BMW",
                model="320d",
                price=25000.0,
                images=["img1.jpg"],
                equipment=["ABS"],
            )
        )
        mock_registry_get.return_value = mock_provider

        response = client.get("/api/v1/vehicle/mobile_de/12345")
        data = response.json()
        assert data["source"] == "mobile_de"
        assert data["external_id"] == "12345"
