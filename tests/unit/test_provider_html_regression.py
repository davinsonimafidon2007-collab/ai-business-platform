"""Regresión offline de parsers HTML (Task A.6).

Usa fixtures estáticas: no requiere red ni proxy.
"""

from __future__ import annotations

from pathlib import Path

from app.providers.autoscout24 import AutoScout24Provider
from app.providers.mobile_de import MobileDeProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestAutoScout24HtmlRegression:
    def test_search_results_parse_at_least_one(self) -> None:
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        assert len(results) >= 1
        first = results[0]
        assert first.external_id
        assert first.brand is not None or first.price is not None

    def test_search_results_bmw_fields(self) -> None:
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        bmw = next((r for r in results if r.brand and "BMW" in r.brand.upper()), results[0])
        assert bmw.price is None or bmw.price >= 500
        if bmw.price is not None:
            assert bmw.price <= 500_000

    def test_search_empty_returns_zero(self) -> None:
        html = _read("autoscout24_search_empty.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        assert results == []

    # --- TASK-016: drift de selectores críticos ---

    def test_search_results_extract_price_selectors(self) -> None:
        """El selector de precio sigue extrayendo valores en el fixture.

        Si el markup de AS24 cambia (clase/atributo del precio), esto falla y
        avisa de drift antes de que afecte a producción.
        """
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        prices = [r.price for r in results if r.price is not None]
        assert prices, "ningún resultado extrajo precio: drift en selector de precio"
        assert all(p > 0 for p in prices)

    def test_search_results_extract_mileage_selectors(self) -> None:
        """El selector de kilometraje sigue extrayendo valores en el fixture."""
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        mileages = [r.mileage for r in results if r.mileage is not None]
        assert mileages, "ningún resultado extrajo kilometraje: drift en selector"
        assert all(m > 0 for m in mileages)

    def test_search_results_extract_external_ids(self) -> None:
        """Los enlaces/detalles siguen extrayendo external_id (drift guard)."""
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        results = provider._parse_search_results(html, "https://www.autoscout24.de/lst")
        assert len(results) >= 1
        assert all(r.external_id for r in results)


class TestMobileDeHtmlRegression:
    def test_search_results_parse_at_least_one(self) -> None:
        html = _read("mobile_de_search_results.html")
        provider = MobileDeProvider()
        results = provider._parse_search_results(html, "https://suchen.mobile.de/fahrzeuge/search.html")
        assert len(results) >= 1
        assert results[0].external_id

    def test_search_empty_returns_zero(self) -> None:
        html = _read("mobile_de_search_empty.html")
        provider = MobileDeProvider()
        results = provider._parse_search_results(html, "https://suchen.mobile.de/fahrzeuge/search.html")
        assert results == []

    # --- TASK-016: drift de selectores críticos ---

    def test_search_results_extract_price_selectors(self) -> None:
        """El selector de precio sigue extrayendo valores en el fixture."""
        html = _read("mobile_de_search_results.html")
        provider = MobileDeProvider()
        results = provider._parse_search_results(html, "https://suchen.mobile.de/fahrzeuge/search.html")
        prices = [r.price for r in results if r.price is not None]
        assert prices, "ningún resultado extrajo precio: drift en selector de precio"
        assert all(p > 0 for p in prices)

    def test_search_results_extract_mileage_selectors(self) -> None:
        """El selector de kilometraje sigue extrayendo valores en el fixture."""
        html = _read("mobile_de_search_results.html")
        provider = MobileDeProvider()
        results = provider._parse_search_results(html, "https://suchen.mobile.de/fahrzeuge/search.html")
        mileages = [r.mileage for r in results if r.mileage is not None]
        assert mileages, "ningún resultado extrajo kilometraje: drift en selector"
        assert all(m > 0 for m in mileages)

    def test_search_results_extract_external_ids(self) -> None:
        """Los enlaces/detalles siguen extrayendo external_id (drift guard)."""
        html = _read("mobile_de_search_results.html")
        provider = MobileDeProvider()
        results = provider._parse_search_results(html, "https://suchen.mobile.de/fahrzeuge/search.html")
        assert len(results) >= 1
        assert all(r.external_id for r in results)