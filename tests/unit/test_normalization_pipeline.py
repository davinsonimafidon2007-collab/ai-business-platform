"""Integration tests for normalization pipeline with repository and service."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.vehicle import Vehicle
from app.normalization.pipeline import NormalizationPipeline, VehicleNormalizer
from app.normalization.schema import NormalizedVehicle
from app.providers.dto import VehicleSearchResult
from app.services.vehicle_service import VehicleService

TEST_USER_ID = str(uuid4())


class MockVehicleRepository:
    """Mock repository for testing."""

    def __init__(self):
        self.vehicles: dict[str, Vehicle] = {}
        self.next_id = 1

    async def create(self, vehicle: Vehicle) -> Vehicle:
        # If vehicle already has an ID (from NormalizedVehicle), use it
        if vehicle.id is None or vehicle.id == "":
            vehicle.id = self.next_id
            self.next_id += 1
        self.vehicles[str(vehicle.id)] = vehicle
        return vehicle

    async def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        return self.vehicles.get(str(vehicle_id))

    async def get_by_external_id(self, source: str, external_id: str, user_id: str | None = None) -> Vehicle | None:
        for v in self.vehicles.values():
            if v.source == source and v.external_id == external_id:
                if user_id is None or str(v.user_id) == str(user_id):
                    return v
        return None

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        user_vehicles = [v for v in self.vehicles.values() if str(v.user_id) == str(user_id)]
        return user_vehicles[skip:skip + limit]

    async def update(self, vehicle: Vehicle) -> Vehicle:
        self.vehicles[str(vehicle.id)] = vehicle
        return vehicle

    async def delete(self, vehicle: Vehicle) -> None:
        self.vehicles.pop(str(vehicle.id), None)


@pytest.fixture
def mock_repo() -> MockVehicleRepository:
    return MockVehicleRepository()


@pytest.fixture
def vehicle_service(mock_repo: MockVehicleRepository) -> VehicleService:
    return VehicleService(
        repository=mock_repo,
        enable_normalization=True,
        min_quality_score=0.3,
    )


@pytest.fixture
def sample_dto() -> VehicleSearchResult:
    return VehicleSearchResult(
        source="autoscout24",
        external_id="31000001",
        url="https://www.autoscout24.de/angebote/bmw-3er-320d-31000001",
        brand="BMW",
        model="3er 320d",
        version="320d",
        year=2020,
        mileage=20000,
        fuel_type="Diesel",
        transmission="Automática",
        power_hp=190,
        displacement_cc=1995,
        location="Berlin 10115 DE",
        seller_type="Dealer",
        first_registration="03-2020",
        price=28500.0,
        currency="EUR",
        vin="WBA3A510XLF123456",
        description="BMW 3er 320d, muy buen estado, histórico completo",
        images=[
            "https://img.autoscout24.de/bmw1.jpg",
            "https://img.autoscout24.de/bmw2.jpg",
        ],
        equipment=["Navi", "Ledersitze", "Klimaautomatik"],
    )


class TestNormalizationPipelineIntegration:
    """Integration tests for NormalizationPipeline with repository."""

    @pytest.mark.asyncio
    async def test_pipeline_process_single(self, mock_repo: MockVehicleRepository, sample_dto: VehicleSearchResult) -> None:
        pipeline = NormalizationPipeline(
            repository=mock_repo,
            min_quality_score=0.3,
        )

        vehicle = await pipeline.process_single(sample_dto, TEST_USER_ID)

        assert vehicle is not None
        assert vehicle.source == "autoscout24"
        assert vehicle.external_id == "31000001"
        assert vehicle.brand == "BMW"
        assert vehicle.price == 28500.0
        assert vehicle.mileage == 20000

    @pytest.mark.asyncio
    async def test_pipeline_process_batch(self, mock_repo: MockVehicleRepository) -> None:
        dtos = [
            VehicleSearchResult(
                source="autoscout24",
                external_id="1",
                brand="BMW",
                model="X5",
                year=2020,
                mileage=50000,
                price=35000.0,
                currency="EUR",
            ),
            VehicleSearchResult(
                source="coches_net",
                external_id="2",
                brand="Audi",
                model="A4",
                year=2021,
                mileage=30000,
                price=28000.0,
                currency="EUR",
            ),
        ]
        pipeline = NormalizationPipeline(repository=mock_repo, min_quality_score=0.3)

        vehicles = await pipeline.process_provider_results(dtos, TEST_USER_ID)

        assert len(vehicles) == 2
        assert vehicles[0].brand == "BMW"
        assert vehicles[1].brand == "Audi"

    @pytest.mark.asyncio
    async def test_pipeline_deduplicates_by_vin(self, mock_repo: MockVehicleRepository) -> None:
        dtos = [
            VehicleSearchResult(
                source="autoscout24",
                external_id="1",
                brand="BMW",
                model="X5",
                year=2020,
                mileage=50000,
                price=35000.0,
                currency="EUR",
                vin="WBA3A510XLF123456",
            ),
            VehicleSearchResult(
                source="mobile_de",
                external_id="2",
                brand="BMW",
                model="X5",
                year=2020,
                mileage=50000,
                price=36000.0,
                currency="EUR",
                vin="WBA3A510XLF123456",
            ),
        ]
        pipeline = NormalizationPipeline(repository=mock_repo, min_quality_score=0.3)

        vehicles = await pipeline.process_provider_results(dtos, TEST_USER_ID)

        assert len(vehicles) == 1
        assert vehicles[0].source == "autoscout24"

    @pytest.mark.asyncio
    async def test_pipeline_rejects_low_quality(self, mock_repo: MockVehicleRepository) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="Test",
            model="Car",
            # Missing year, mileage, price
        )
        pipeline = NormalizationPipeline(repository=mock_repo, min_quality_score=0.5)

        vehicle = await pipeline.process_single(dto, TEST_USER_ID)

        assert vehicle is None

    @pytest.mark.asyncio
    async def test_pipeline_detects_corrupt_listing(self, mock_repo: MockVehicleRepository) -> None:
        dto = VehicleSearchResult(
            source="test",
            external_id="1",
            brand="BMW",
            model="X5",
            year=2023,
            mileage=5000,
            price=500.0,  # Suspiciously low
            currency="EUR",
            images=[],
            equipment=[],
            description="",
        )
        pipeline = NormalizationPipeline(
            repository=mock_repo,
            min_quality_score=0.8,  # Higher threshold to catch corrupt
            enable_corrupt_detection=True,
        )

        vehicle = await pipeline.process_single(dto, TEST_USER_ID)

        assert vehicle is None  # Rejected due to corrupt detection lowering quality below threshold


class TestVehicleServiceWithNormalization:
    """Tests for VehicleService with normalization enabled."""

    @pytest.mark.asyncio
    async def test_import_from_provider_result(
        self,
        vehicle_service: VehicleService,
        sample_dto: VehicleSearchResult,
    ) -> None:
        vehicle = await vehicle_service.import_from_provider_result(sample_dto, TEST_USER_ID)

        assert vehicle is not None
        assert vehicle.brand == "BMW"
        assert vehicle.model == "3er 320d"
        assert vehicle.price == 28500.0
        assert vehicle.images == [
            "https://img.autoscout24.de/bmw1.jpg",
            "https://img.autoscout24.de/bmw2.jpg",
        ]

    @pytest.mark.asyncio
    async def test_import_updates_existing(
        self,
        vehicle_service: VehicleService,
        sample_dto: VehicleSearchResult,
    ) -> None:
        # First import
        vehicle1 = await vehicle_service.import_from_provider_result(sample_dto, TEST_USER_ID)
        assert vehicle1 is not None
        original_id = vehicle1.id

        # Second import with updated price
        updated_dto = VehicleSearchResult(
            source="autoscout24",
            external_id="31000001",
            brand="BMW",
            model="3er 320d",
            year=2020,
            mileage=21000,
            price=27500.0,  # Price dropped
            currency="EUR",
        )
        vehicle2 = await vehicle_service.import_from_provider_result(updated_dto, TEST_USER_ID)

        assert vehicle2 is not None
        assert vehicle2.id == original_id
        assert vehicle2.price == 27500.0
        assert vehicle2.mileage == 21000

    @pytest.mark.asyncio
    async def test_import_multiple_users_isolated(
        self,
        vehicle_service: VehicleService,
        sample_dto: VehicleSearchResult,
    ) -> None:
        other_user = str(uuid4())

        vehicle_a = await vehicle_service.import_from_provider_result(sample_dto, TEST_USER_ID)
        vehicle_b = await vehicle_service.import_from_provider_result(sample_dto, other_user)

        assert vehicle_a is not None
        assert vehicle_b is not None
        assert vehicle_a.id != vehicle_b.id
        assert str(vehicle_a.user_id) == TEST_USER_ID
        assert str(vehicle_b.user_id) == other_user

    @pytest.mark.asyncio
    async def test_search_and_import_workflow(
        self,
        vehicle_service: VehicleService,
        sample_dto: VehicleSearchResult,
    ) -> None:
        # Mock provider
        class MockProvider:
            @property
            def source_name(self) -> str:
                return "mock"

            async def search(self, query: str, **kwargs) -> list[VehicleSearchResult]:
                return [sample_dto]

        provider = MockProvider()

        vehicles = await vehicle_service.search_and_import(provider, "BMW X5", TEST_USER_ID)

        assert len(vehicles) == 1
        assert vehicles[0].brand == "BMW"


class TestVehicleNormalizerIntegration:
    """Tests for VehicleNormalizer without repository."""

    def test_normalize_without_persistence(self, sample_dto: VehicleSearchResult) -> None:
        normalizer = VehicleNormalizer()
        norm = normalizer.normalize(sample_dto)

        assert isinstance(norm, NormalizedVehicle)
        assert norm.source == "autoscout24"
        assert norm.brand == "BMW"
        assert norm.price_eur == Decimal("28500.00")

    def test_normalize_batch_returns_normalized_vehicles(self) -> None:
        dtos = [
            VehicleSearchResult(
                source="autoscout24",
                external_id="1",
                brand="BMW",
                model="X5",
                year=2020,
                mileage=50000,
                price=35000.0,
            ),
            VehicleSearchResult(
                source="coches_net",
                external_id="2",
                brand="Audi",
                model="A4",
                year=2021,
                mileage=30000,
                price=28000.0,
            ),
        ]
        normalizer = VehicleNormalizer()
        norms = normalizer.normalize_batch(dtos)

        assert len(norms) == 2
        assert all(isinstance(n, NormalizedVehicle) for n in norms)
        assert norms[0].brand == "BMW"
        assert norms[1].brand == "Audi"

    def test_to_sqlalchemy_model(self, sample_dto: VehicleSearchResult) -> None:
        normalizer = VehicleNormalizer()
        norm = normalizer.normalize(sample_dto)
        vehicle = normalizer.to_sqlalchemy_model(norm, TEST_USER_ID)

        assert isinstance(vehicle, Vehicle)
        assert vehicle.source == "autoscout24"
        assert vehicle.brand == "BMW"
        assert vehicle.price == 28500.0
        assert vehicle.user_id == TEST_USER_ID


class TestBackwardsCompatibility:
    """Tests ensuring legacy import path still works."""

    @pytest.mark.asyncio
    async def test_legacy_import_when_normalization_disabled(
        self,
        mock_repo: MockVehicleRepository,
        sample_dto: VehicleSearchResult,
    ) -> None:
        service = VehicleService(
            repository=mock_repo,
            enable_normalization=False,
        )

        vehicle = await service.import_from_provider_result(sample_dto, TEST_USER_ID)

        assert vehicle is not None
        assert vehicle.brand == "BMW"
        assert vehicle.price == 28500.0

    @pytest.mark.asyncio
    async def test_legacy_update_from_dto(
        self,
        vehicle_service: VehicleService,
        sample_dto: VehicleSearchResult,
    ) -> None:
        # Create vehicle first
        vehicle = await vehicle_service.import_from_provider_result(sample_dto, TEST_USER_ID)
        original_updated_at = vehicle.updated_at

        # Update with new data
        updated_dto = VehicleSearchResult(
            source="autoscout24",
            external_id="31000001",
            brand="BMW",
            model="3er 320d",
            year=2020,
            mileage=25000,
            price=27000.0,
            currency="EUR",
        )

        import asyncio
        await asyncio.sleep(0.1)  # Ensure timestamp changes

        updated = await vehicle_service.import_from_provider_result(updated_dto, TEST_USER_ID)

        assert updated.id == vehicle.id
        assert updated.price == 27000.0
        assert updated.mileage == 25000
        assert updated.updated_at > original_updated_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])