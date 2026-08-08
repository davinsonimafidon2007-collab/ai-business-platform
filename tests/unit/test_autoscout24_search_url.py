"""E2E.MANUAL.PASS.1: AS24 debe construir la URL de listados desde criterios.

Bug detectado en el run manual: ``VehicleProvider.search()`` descarga el
``query`` tal cual, pero ``SearchOrchestrator`` le pasaba el término crudo
("BMW"). Resultado: GET https://www.autoscout24.de/BMW → 404, que el
orquestador capturaba y convertía en 200 con 0 resultados (fallo silencioso),
mientras el provider en directo sí devolvía 20 listings.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.providers.autoscout24 import AutoScout24Provider


def _provider() -> AutoScout24Provider:
    return AutoScout24Provider(http_client=object())


def test_plain_term_becomes_listing_url_not_path() -> None:
    """"BMW" → /lst/bmw (no autoscout24.de/BMW, que daba 404)."""
    url = _provider().build_search_url("BMW")

    parsed = urlparse(url)
    assert parsed.netloc == "www.autoscout24.de"
    assert parsed.path == "/lst/bmw"
    assert parsed.path != "/BMW"


def test_absolute_url_is_preserved() -> None:
    """Si ya viene una URL (scripts de verificación), se respeta."""
    original = (
        "https://www.autoscout24.de/lst/bmw"
        "?atype=C&cy=D&desc=0&sort=standard&ustate=N%2CU"
    )

    assert _provider().build_search_url(original) == original


def test_brand_and_model_go_in_path() -> None:
    url = _provider().build_search_url("", brand="BMW", model="Serie 3")

    assert urlparse(url).path == "/lst/bmw/serie-3"


def test_free_text_splits_into_brand_and_model() -> None:
    url = _provider().build_search_url("BMW 320")

    assert urlparse(url).path == "/lst/bmw/320"


def test_orchestrator_budget_kwargs_map_to_price_filters() -> None:
    """SearchOrchestrator envía budget_min/budget_max, no min_price/max_price."""
    url = _provider().build_search_url("BMW", budget_min=5000, budget_max=15000.0)

    query = parse_qs(urlparse(url).query)
    assert query["pricefrom"] == ["5000"]
    # El float no debe colarse como "15000.0" en la query.
    assert query["priceto"] == ["15000"]


def test_year_mileage_fuel_and_transmission_filters() -> None:
    url = _provider().build_search_url(
        "BMW",
        min_year=2015,
        max_mileage=120000,
        fuel_type="Diesel",
        transmission="Automática",
    )

    query = parse_qs(urlparse(url).query)
    assert query["fregfrom"] == ["2015"]
    assert query["kmto"] == ["120000"]
    assert query["fuel"] == ["D"]
    assert query["gear"] == ["A"]


def test_base_query_params_always_present() -> None:
    query = parse_qs(urlparse(_provider().build_search_url("BMW")).query)

    assert query["atype"] == ["C"]
    assert query["cy"] == ["D"]
    assert query["ustate"] == ["N,U"]
