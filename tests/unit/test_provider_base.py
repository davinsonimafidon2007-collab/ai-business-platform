import pytest

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult


def test_vehicle_provider_is_abstract() -> None:
    """Verifica que VehicleProvider no se puede instanciar directamente."""
    with pytest.raises(TypeError):
        VehicleProvider()  # type: ignore[abstract]


def test_vehicle_search_result_dto() -> None:
    result = VehicleSearchResult(source="mobile_de", external_id="ext-123")

    assert result.source == "mobile_de"
    assert result.external_id == "ext-123"
    assert result.images == []
    assert result.equipment == []
    assert result.raw_data == {}


def test_vehicle_search_result_with_all_fields() -> None:
    result = VehicleSearchResult(
        source="mobile_de",
        external_id="ext-456",
        url="https://mobile.de/vehicle/456",
        brand="BMW",
        model="X5",
        year=2020,
        price=35000.0,
        currency="EUR",
        images=["img1.jpg", "img2.jpg"],
        equipment=["Climatronic", "Parking sensors"],
    )

    assert result.brand == "BMW"
    assert result.model == "X5"
    assert result.year == 2020
    assert result.price == 35000.0
    assert len(result.images) == 2
    assert len(result.equipment) == 2


def test_vehicle_detail_dto() -> None:
    detail = VehicleDetail(source="autoscout24", external_id="ext-789")

    assert detail.source == "autoscout24"
    assert detail.external_id == "ext-789"
    assert detail.vin is None
    assert detail.description is None


def test_vehicle_provider_extract_emissions_euro_norm() -> None:
    """Verifica la extracción y normalización de la clasificación ambiental Euro (TASK-013)."""
    from bs4 import BeautifulSoup

    class TestProvider(VehicleProvider):
        @property
        def source_name(self) -> str:
            return "test_provider"

        def _find_listing_nodes(self, soup: BeautifulSoup) -> list:
            return []

    provider = TestProvider()

    # 1) Euro norm pattern
    soup1 = BeautifulSoup("<html><body>Normativa Euro 6d-temp disponible</body></html>", "lxml")
    assert provider._extract_emissions(soup1) == "Euro 6d-temp"

    # 2) CO2 emissions pattern fallback
    soup2 = BeautifulSoup("<html><body>Emisiones de CO2: 120 g/km combinadas</body></html>", "lxml")
    assert provider._extract_emissions(soup2) == "120 g/km"

    # 3) Empty/Missing pattern
    soup3 = BeautifulSoup("<html><body>Sin especificar el tipo de coche</body></html>", "lxml")
    assert provider._extract_emissions(soup3) is None