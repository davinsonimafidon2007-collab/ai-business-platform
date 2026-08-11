import pytest

from app.models.vehicle import Vehicle
from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.registry import ProviderRegistry
from app.repositories.vehicle_repository import VehicleRepository
from app.services.vehicle_service import VehicleService


class MockVehicleRepository(VehicleRepository):
    """Mock repository for testing."""

    def __init__(self):
        self.vehicles = {}
        self.next_id = 1

    async def create(self, vehicle: Vehicle) -> Vehicle:
        vehicle.id = self.next_id
        self.vehicles[self.next_id] = vehicle
        self.next_id += 1
        return vehicle

    async def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        for v in self.vehicles.values():
            if str(v.id) == str(vehicle_id):
                return v
        return None

    async def get_by_external_id(self, source: str, external_id: str) -> Vehicle | None:
        for v in self.vehicles.values():
            if v.source == source and v.external_id == external_id:
                return v
        return None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        return list(self.vehicles.values())[skip : skip + limit]

    async def update(self, vehicle: Vehicle) -> Vehicle:
        self.vehicles[vehicle.id] = vehicle
        return vehicle

    async def delete(self, vehicle: Vehicle) -> None:
        self.vehicles.pop(vehicle.id, None)


class MockProvider(VehicleProvider):
    """Mock provider for testing."""

    @property
    def source_name(self) -> str:
        return "mock_provider"

    def _find_listing_nodes(self, soup: object) -> list[object]:
        return []

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        return [
            VehicleSearchResult(
                source="mock_provider",
                external_id="ext-1",
                brand="BMW",
                model="X5",
                year=2020,
                price=35000.0,
                currency="EUR",
            )
        ]

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        return VehicleDetail(
            source="mock_provider",
            external_id=external_id,
            brand="BMW",
            model="X5",
            year=2020,
            price=35000.0,
            currency="EUR",
        )

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        return VehicleSearchResult(
            source="mock_provider",
            external_id="ext-1",
            brand="BMW",
            model="X5",
        )


@pytest.fixture
def vehicle_repository():
    return MockVehicleRepository()


@pytest.fixture
def vehicle_service(vehicle_repository):
    return VehicleService(vehicle_repository)


@pytest.fixture(autouse=True)
def clear_registry():
    ProviderRegistry.clear()


@pytest.mark.asyncio
async def test_search_from_provider(vehicle_service):
    """Test searching vehicles from a provider."""
    provider = MockProvider()
    results = await vehicle_service.search_from_provider(provider, "BMW X5")

    assert len(results) == 1
    assert results[0].source == "mock_provider"
    assert results[0].external_id == "ext-1"
    assert results[0].brand == "BMW"
    assert results[0].model == "X5"
    assert results[0].year == 2020
    assert results[0].price == 35000.0
    assert results[0].currency == "EUR"


@pytest.mark.asyncio
async def test_import_from_provider_creates_new_vehicle(vehicle_service):
    """Test importing a vehicle from provider when it doesn't exist."""
    result = VehicleSearchResult(
        source="mock_provider",
        external_id="ext-new",
        brand="Audi",
        model="A4",
        year=2021,
        price=30000.0,
        currency="EUR",
        url="https://example.com/vehicle/ext-new",
        fuel_type="Diesel",
        transmission="Automatic",
        mileage=15000,
        images=["img1.jpg", "img2.jpg"],
        equipment=["GPS", "Leather seats"],
    )

    vehicle = await vehicle_service.import_from_provider_result(result)

    assert vehicle.id is not None
    assert vehicle.source == "mock_provider"
    assert vehicle.external_id == "ext-new"
    assert vehicle.brand == "Audi"
    assert vehicle.model == "A4"
    assert vehicle.year == 2021
    assert vehicle.price == 30000.0
    assert vehicle.currency == "EUR"
    assert vehicle.url == "https://example.com/vehicle/ext-new"
    assert vehicle.fuel_type == "Diesel"
    assert vehicle.transmission == "Automatic"
    assert vehicle.mileage == 15000
    assert vehicle.images == ["img1.jpg", "img2.jpg"]
    assert vehicle.equipment == "GPS,Leather seats"


@pytest.mark.asyncio
async def test_import_from_provider_updates_existing_vehicle(vehicle_service):
    """Test importing a vehicle from provider when it already exists."""
    # First import
    result1 = VehicleSearchResult(
        source="mock_provider",
        external_id="ext-existing",
        brand="BMW",
        model="X5",
        year=2020,
        price=35000.0,
        currency="EUR",
    )
    vehicle1 = await vehicle_service.import_from_provider_result(result1)
    original_updated_at = vehicle1.updated_at

    # Second import with updated data
    result2 = VehicleSearchResult(
        source="mock_provider",
        external_id="ext-existing",
        brand="BMW",
        model="X5",
        year=2020,
        price=32000.0,  # Price changed
        currency="EUR",
        mileage=5000,  # New field
    )

    import asyncio
    await asyncio.sleep(0.1)  # Ensure timestamp changes

    vehicle2 = await vehicle_service.import_from_provider_result(result2)

    assert vehicle2.id == vehicle1.id
    assert vehicle2.price == 32000.0  # Updated price
    assert vehicle2.mileage == 5000  # New field added
    assert vehicle2.updated_at > original_updated_at  # Timestamp updated


@pytest.mark.asyncio
async def test_import_from_provider_with_none_values(vehicle_service):
    """Test that None values are handled correctly during import."""
    result = VehicleSearchResult(
        source="mock_provider",
        external_id="ext-partial",
        brand="BMW",
        model="X3",
        year=2019,
        price=28000.0,
        currency="EUR",
        url=None,
        version=None,
        mileage=None,
        fuel_type=None,
    )

    vehicle = await vehicle_service.import_from_provider_result(result)

    assert vehicle.source == "mock_provider"
    assert vehicle.external_id == "ext-partial"
    assert vehicle.brand == "BMW"
    assert vehicle.model == "X3"
    assert vehicle.year == 2019
    assert vehicle.price == 28000.0
    assert vehicle.url is None
    assert vehicle.version is None
    assert vehicle.mileage is None
    assert vehicle.fuel_type is None


@pytest.mark.asyncio
async def test_import_from_provider_empty_lists(vehicle_service):
    """Test that empty lists for images and equipment are handled correctly."""
    result = VehicleSearchResult(
        source="mock_provider",
        external_id="ext-empty",
        brand="BMW",
        model="X1",
        year=2018,
        price=25000.0,
        currency="EUR",
        images=[],
        equipment=[],
    )

    vehicle = await vehicle_service.import_from_provider_result(result)

    assert vehicle.images is None
    assert vehicle.equipment is None


@pytest.mark.asyncio
async def test_search_and_import_workflow(vehicle_service):
    """Test the complete workflow: search then import."""
    provider = MockProvider()

    # Search
    search_results = await vehicle_service.search_from_provider(provider, "BMW X5")
    assert len(search_results) == 1

    # Import first result
    vehicle = await vehicle_service.import_from_provider_result(search_results[0])
    assert vehicle.brand == "BMW"
    assert vehicle.model == "X5"

    # Verify it's persisted
    retrieved = await vehicle_service.get_vehicle_by_external_id("mock_provider", "ext-1")
    assert retrieved is not None
    assert retrieved.id == vehicle.id