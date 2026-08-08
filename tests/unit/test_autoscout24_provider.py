"""Tests para el AutoScout24Provider.

Todos los tests utilizan HTML almacenado localmente en ``tests/fixtures``
para que no dependan de Internet. Sigue la misma estructura que
test_mobile_de_provider.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.autoscout24 import AutoScout24Provider
from app.providers.dto import VehicleDetail, VehicleSearchResult

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    """Carga un archivo HTML de fixtures como texto."""
    path = FIXTURES_DIR / name
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider() -> AutoScout24Provider:
    """Crea un AutoScout24Provider para tests."""
    return AutoScout24Provider()


@pytest.fixture
def search_html() -> str:
    return _load_fixture("autoscout24_search_results.html")


@pytest.fixture
def detail_html() -> str:
    return _load_fixture("autoscout24_vehicle_detail.html")


@pytest.fixture
def empty_html() -> str:
    return _load_fixture("autoscout24_search_empty.html")


# ---------------------------------------------------------------------------
# Propiedades básicas
# ---------------------------------------------------------------------------


def test_source_name(provider: AutoScout24Provider) -> None:
    assert provider.source_name == "autoscout24"


def test_base_url_default(provider: AutoScout24Provider) -> None:
    assert provider._base_url == "https://www.autoscout24.de"


def test_base_url_custom() -> None:
    p = AutoScout24Provider(base_url="https://custom.autoscout24.de")
    assert p._base_url == "https://custom.autoscout24.de"


# ---------------------------------------------------------------------------
# Parsing de resultados de búsqueda
# ---------------------------------------------------------------------------


def test_parse_search_results_returns_list(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    assert isinstance(results, list)
    assert len(results) == 3  # 3 anuncios válidos (el 4º no tiene enlace)


def test_parse_search_results_all_are_vehicle_search_result(
    provider: AutoScout24Provider, search_html: str
) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    for r in results:
        assert isinstance(r, VehicleSearchResult)
        assert r.source == "autoscout24"


def test_parse_search_results_external_ids(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    ids = [r.external_id for r in results]
    assert "31000001" in ids
    assert "32000002" in ids
    assert "33000003" in ids


def test_parse_search_results_urls(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    urls = [r.url for r in results]
    assert any("31000001" in u for u in urls)
    assert any("32000002" in u for u in urls)
    assert any("33000003" in u for u in urls)


def test_parse_search_results_brands(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    brands = [r.brand for r in results]
    assert "BMW" in brands
    assert "Audi" in brands
    assert "Mercedes-Benz" in brands


def test_parse_search_results_models(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    models = [r.model for r in results]
    assert "3er 320d" in models
    assert "A4 40 TFSI" in models
    assert "C-Klasse C200" in models


def test_parse_search_results_prices(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    prices = {r.external_id: r.price for r in results}
    assert prices["31000001"] == 28500.0
    assert prices["32000002"] == 32990.0
    assert prices["33000003"] == 35500.0


def test_parse_search_results_mileage(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    mileage = {r.external_id: r.mileage for r in results}
    assert mileage["31000001"] == 20000
    assert mileage["32000002"] == 15000
    assert mileage["33000003"] == 30000


def test_parse_search_results_year(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    years = {r.external_id: r.year for r in results}
    assert years["31000001"] == 2020
    assert years["32000002"] == 2021
    assert years["33000003"] == 2019


def test_parse_search_results_fuel_type(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    fuels = {r.external_id: r.fuel_type for r in results}
    assert fuels["31000001"] == "Diesel"
    assert fuels["32000002"] == "Gasolina"
    assert fuels["33000003"] == "Gasolina"


def test_parse_search_results_transmission(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    transmissions = {r.external_id: r.transmission for r in results}
    assert transmissions["31000001"] == "Automática"
    assert transmissions["32000002"] == "Manual"
    assert transmissions["33000003"] == "Automática"


def test_parse_search_results_power(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    powers = {r.external_id: r.power_hp for r in results}
    assert powers["31000001"] == 190
    assert powers["32000002"] == 190
    assert powers["33000003"] == 184


def test_parse_search_results_location(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    locations = {r.external_id: r.location for r in results}
    assert "Berlin" in locations["31000001"]
    assert "München" in locations["32000002"]
    assert "Hamburg" in locations["33000003"]


def test_parse_search_results_images(provider: AutoScout24Provider, search_html: str) -> None:
    results = provider._parse_search_results(search_html, "https://www.autoscout24.de/search")
    images = {r.external_id: r.images for r in results}
    assert len(images["31000001"]) == 2
    assert len(images["32000002"]) == 1
    assert len(images["33000003"]) == 2
    # Verificar que las imágenes son URLs absolutas
    for img_url in images["31000001"]:
        assert img_url.startswith("https://")


def test_parse_search_results_empty(provider: AutoScout24Provider, empty_html: str) -> None:
    results = provider._parse_search_results(empty_html, "https://www.autoscout24.de/search")
    assert results == []


# ---------------------------------------------------------------------------
# Parsing de detalle de vehículo
# ---------------------------------------------------------------------------


def test_parse_vehicle_detail_returns_vehicle_detail(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert isinstance(detail, VehicleDetail)
    assert detail.source == "autoscout24"


def test_parse_vehicle_detail_external_id(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.external_id == "31000001"


def test_parse_vehicle_detail_url(provider: AutoScout24Provider, detail_html: str) -> None:
    url = "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001"
    detail = provider._parse_vehicle_detail(detail_html, url)
    assert detail.url == url


def test_parse_vehicle_detail_brand_model(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.brand == "BMW"
    assert detail.model == "3er 320d"


def test_parse_vehicle_detail_price(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.price == 28500.0


def test_parse_vehicle_detail_mileage(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.mileage == 20000


def test_parse_vehicle_detail_year(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.year == 2020


def test_parse_vehicle_detail_fuel_type(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.fuel_type == "Diesel"


def test_parse_vehicle_detail_transmission(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.transmission == "Automática"


def test_parse_vehicle_detail_power(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.power_hp == 190


def test_parse_vehicle_detail_location(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert "Berlin" in detail.location


def test_parse_vehicle_detail_images(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert len(detail.images) == 3
    for img_url in detail.images:
        assert img_url.startswith("https://")


def test_parse_vehicle_detail_description(provider: AutoScout24Provider, detail_html: str) -> None:
    detail = provider._parse_vehicle_detail(detail_html, "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001")
    assert detail.description is not None
    assert "BMW 3er" in detail.description


# ---------------------------------------------------------------------------
# Métodos de extracción individuales
# ---------------------------------------------------------------------------


def test_extract_external_id_from_url() -> None:
    p = AutoScout24Provider()
    assert p._extract_external_id("https://www.autoscout24.de/angebote/bmw-3er-320d-berlin-31000001") == "31000001"
    assert p._extract_external_id("https://www.autoscout24.de/angebote/audi-a4-32000002") == "32000002"
    assert p._extract_external_id("https://www.autoscout24.de/angebote/12345/") == "12345"
    assert p._extract_external_id(None) is None
    assert p._extract_external_id("https://example.com/no-id") == "https://example.com/no-id"


def test_extract_url_from_tag() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<a href="https://www.autoscout24.de/angebote/12345">Link</a>'
    soup = BeautifulSoup(html, "lxml")
    tag = soup.select_one("a")
    assert p._extract_url(tag) == "https://www.autoscout24.de/angebote/12345"


def test_extract_url_relative() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<a href="/angebote/12345">Link</a>'
    soup = BeautifulSoup(html, "lxml")
    tag = soup.select_one("a")
    assert p._extract_url(tag) == "https://www.autoscout24.de/angebote/12345"


def test_extract_url_protocol_relative() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<a href="//www.autoscout24.de/angebote/12345">Link</a>'
    soup = BeautifulSoup(html, "lxml")
    tag = soup.select_one("a")
    assert p._extract_url(tag) == "https://www.autoscout24.de/angebote/12345"


def test_extract_url_none() -> None:
    p = AutoScout24Provider()
    assert p._extract_url(None) is None


def test_parse_price_text() -> None:
    p = AutoScout24Provider()
    assert p._parse_price_text("28.500 €") == 28500.0
    assert p._parse_price_text("32.990 €") == 32990.0
    assert p._parse_price_text("12.345,- €") == 12345.0
    assert p._parse_price_text("12345 EUR") == 12345.0
    assert p._parse_price_text("Sin precio") is None
    assert p._parse_price_text("") is None


def test_extract_mileage() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<div>20.000 km</div>'
    soup = BeautifulSoup(html, "lxml")
    assert p._extract_mileage(soup) == 20000

    html2 = '<div>15000 km</div>'
    soup2 = BeautifulSoup(html2, "lxml")
    assert p._extract_mileage(soup2) == 15000


def test_extract_year_from_date() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<div>01/2020</div>'
    soup = BeautifulSoup(html, "lxml")
    assert p._extract_year(soup) == 2020


def test_extract_year_from_text() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<div>Primera matriculación: 2019</div>'
    soup = BeautifulSoup(html, "lxml")
    assert p._extract_year(soup) == 2019


def test_extract_fuel_types() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    for fuel_text, expected in [
        ("Diesel", "Diesel"),
        ("Benzin", "Gasolina"),
        ("Elektro", "Eléctrico"),
        ("Hybrid", "Híbrido"),
        ("Wasserstoff", "Hidrógeno"),
        ("LPG", "Gas"),
    ]:
        soup = BeautifulSoup(f"<div>{fuel_text}</div>", "lxml")
        assert p._extract_fuel(soup) == expected, f"Failed for {fuel_text}"


def test_extract_transmission_types() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    for trans_text, expected in [
        ("Schaltgetriebe", "Manual"),
        ("Automatik", "Automática"),
        ("Manual", "Manual"),
    ]:
        soup = BeautifulSoup(f"<div>{trans_text}</div>", "lxml")
        assert p._extract_transmission(soup) == expected, f"Failed for {trans_text}"


def test_extract_power() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = '<div>190 hp</div>'
    soup = BeautifulSoup(html, "lxml")
    assert p._extract_power(soup) == 190

    html2 = '<div>150 PS</div>'
    soup2 = BeautifulSoup(html2, "lxml")
    assert p._extract_power(soup2) is None  # "PS" no está en el patrón


def test_split_brand_model() -> None:
    p = AutoScout24Provider()
    assert p._split_brand_model("BMW 3er 320d") == ("BMW", "3er 320d")
    assert p._split_brand_model("Audi A4") == ("Audi", "A4")
    assert p._split_brand_model("Seat") == ("Seat", None)
    assert p._split_brand_model("") == (None, None)
    assert p._split_brand_model(None) == (None, None)


def test_normalize_image_url() -> None:
    p = AutoScout24Provider()
    assert p._normalize_image_url("//img.autoscout24.de/1.jpg") == "https://img.autoscout24.de/1.jpg"
    assert p._normalize_image_url("/images/1.jpg") == "https://www.autoscout24.de/images/1.jpg"
    assert p._normalize_image_url("https://img.autoscout24.de/1.jpg") == "https://img.autoscout24.de/1.jpg"


def test_extract_images_dedup() -> None:
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()
    html = """
    <div>
        <img data-src="https://img.autoscout24.de/1.jpg">
        <img data-src="https://img.autoscout24.de/1.jpg">
        <img data-src="https://img.autoscout24.de/2.jpg">
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    images = p._extract_images(soup)
    assert len(images) == 2
    assert "https://img.autoscout24.de/1.jpg" in images
    assert "https://img.autoscout24.de/2.jpg" in images


# ---------------------------------------------------------------------------
# normalize_vehicle
# ---------------------------------------------------------------------------


def test_normalize_vehicle_search_result() -> None:
    p = AutoScout24Provider()
    raw = {
        "external_id": "12345",
        "url": "https://www.autoscout24.de/angebote/bmw-x5-12345",
        "brand": "BMW",
        "model": "X5",
        "year": 2020,
        "price": 35000.0,
        "mileage": 15000,
        "fuel_type": "Gasolina",
        "transmission": "Automática",
        "power_hp": 250,
        "images": ["img1.jpg"],
    }
    result = p.normalize_vehicle(raw)
    assert isinstance(result, VehicleSearchResult)
    assert result.source == "autoscout24"
    assert result.external_id == "12345"
    assert result.brand == "BMW"
    assert result.model == "X5"
    assert result.year == 2020
    assert result.price == 35000.0
    assert result.mileage == 15000
    assert result.fuel_type == "Gasolina"
    assert result.transmission == "Automática"
    assert result.power_hp == 250
    assert result.images == ["img1.jpg"]


def test_normalize_vehicle_detail() -> None:
    p = AutoScout24Provider()
    raw = {
        "_type": "detail",
        "external_id": "12345",
        "brand": "BMW",
        "model": "X5",
        "description": "Un coche de ejemplo",
    }
    result = p.normalize_vehicle(raw)
    assert isinstance(result, VehicleDetail)
    assert result.source == "autoscout24"
    assert result.external_id == "12345"
    assert result.brand == "BMW"
    assert result.model == "X5"
    assert result.description == "Un coche de ejemplo"


# ---------------------------------------------------------------------------
# Búsqueda y get_vehicle con HTTP client mockeado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_with_mocked_http(provider: AutoScout24Provider, search_html: str) -> None:
    """Test que search() descarga HTML y parsea resultados."""
    mock_response = MagicMock()
    mock_response.text = search_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        results = await provider.search("https://www.autoscout24.de/search")

    assert len(results) == 3
    assert results[0].source == "autoscout24"
    assert results[0].external_id == "31000001"
    assert results[0].brand == "BMW"
    assert results[0].model == "3er 320d"


@pytest.mark.asyncio
async def test_search_empty_results_with_mocked_http(provider: AutoScout24Provider, empty_html: str) -> None:
    mock_response = MagicMock()
    mock_response.text = empty_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        results = await provider.search("https://www.autoscout24.de/search")

    assert results == []


@pytest.mark.asyncio
async def test_get_vehicle_with_mocked_http(provider: AutoScout24Provider, detail_html: str) -> None:
    mock_response = MagicMock()
    mock_response.text = detail_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    url = "https://www.autoscout24.de/angebote/bmw-3er-320d-31000001"
    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        detail = await provider.get_vehicle(url)

    assert isinstance(detail, VehicleDetail)
    assert detail.external_id == "31000001"
    assert detail.brand == "BMW"
    assert detail.model == "3er 320d"
    assert detail.price == 28500.0


@pytest.mark.asyncio
async def test_get_vehicle_with_external_id(provider: AutoScout24Provider, detail_html: str) -> None:
    mock_response = MagicMock()
    mock_response.text = detail_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        detail = await provider.get_vehicle("31000001")

    assert detail.external_id == "31000001"


# ---------------------------------------------------------------------------
# Integración con VehicleService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_from_vehicle_service(search_html: str) -> None:
    """Test que VehicleService puede usar AutoScout24Provider para buscar."""
    from app.services.vehicle_service import VehicleService
    from tests.unit.test_vehicle_service_providers import MockVehicleRepository

    provider = AutoScout24Provider()
    service = VehicleService(MockVehicleRepository())

    mock_response = MagicMock()
    mock_response.text = search_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        results = await service.search_from_provider(provider, "https://www.autoscout24.de/search")

    assert len(results) == 3
    assert results[0].source == "autoscout24"
    assert results[0].external_id == "31000001"


@pytest.mark.asyncio
async def test_import_from_provider_result(search_html: str) -> None:
    """Test que VehicleService puede importar resultados de AutoScout24Provider."""
    from app.services.vehicle_service import VehicleService
    from tests.unit.test_vehicle_service_providers import MockVehicleRepository

    provider = AutoScout24Provider()
    service = VehicleService(MockVehicleRepository())

    mock_response = MagicMock()
    mock_response.text = search_html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(provider, "_get_client", new_callable=AsyncMock, return_value=mock_client):
        results = await service.search_from_provider(provider, "https://www.autoscout24.de/search")

    vehicle = await service.import_from_provider_result(results[0])

    assert vehicle.source == "autoscout24"
    assert vehicle.external_id == "31000001"
    assert vehicle.brand == "BMW"
    assert vehicle.model == "3er 320d"
    assert vehicle.year == 2020
    assert vehicle.price == 28500.0
    assert vehicle.mileage == 20000
    assert vehicle.fuel_type == "Diesel"
    assert vehicle.transmission == "Automática"
    assert vehicle.power_hp == 190


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_parse_search_results_no_listings(provider: AutoScout24Provider) -> None:
    html = "<html><body><p>No hay nada</p></body></html>"
    results = provider._parse_search_results(html, "https://www.autoscout24.de/search")
    assert results == []


def test_parse_vehicle_detail_no_data(provider: AutoScout24Provider) -> None:
    html = "<html><body><p>Sin datos</p></body></html>"
    detail = provider._parse_vehicle_detail(html, "https://www.autoscout24.de/angebote/12345")
    assert isinstance(detail, VehicleDetail)
    assert detail.external_id == "12345"
    assert detail.brand is None
    assert detail.model is None
    assert detail.price is None


def test_find_listing_nodes_multiple_strategies() -> None:
    """Test que _find_listing_nodes detecta diferentes formatos de HTML."""
    from bs4 import BeautifulSoup

    p = AutoScout24Provider()

    # Formato 1: article.cld-list-item (AutoScout24)
    html1 = '<article class="cld-list-item"><a href="/1">A</a></article>'
    soup1 = BeautifulSoup(html1, "lxml")
    assert len(p._find_listing_nodes(soup1)) == 1

    # Formato 2: article.listing
    html2 = '<article class="listing"><a href="/1">A</a></article>'
    soup2 = BeautifulSoup(html2, "lxml")
    assert len(p._find_listing_nodes(soup2)) == 1

    # Formato 3: div con data-listing-id
    html3 = '<div data-listing-id="123"><a href="/1">A</a></div>'
    soup3 = BeautifulSoup(html3, "lxml")
    assert len(p._find_listing_nodes(soup3)) == 1

    # Formato 4: div con clase "ListItem"
    html4 = '<div class="ListItem"><a href="/1">A</a></div>'
    soup4 = BeautifulSoup(html4, "lxml")
    assert len(p._find_listing_nodes(soup4)) == 1

    # Sin nodos
    html5 = '<div class="other">No listings</div>'
    soup5 = BeautifulSoup(html5, "lxml")
    assert len(p._find_listing_nodes(soup5)) == 0


def test_provider_is_subclass_of_vehicle_provider() -> None:
    from app.providers.base import VehicleProvider

    assert issubclass(AutoScout24Provider, VehicleProvider)


def test_provider_context_manager() -> None:
    """Test que el provider funciona como context manager."""
    import asyncio

    async def _run():
        async with AutoScout24Provider() as p:
            assert p.source_name == "autoscout24"

    asyncio.run(_run())

