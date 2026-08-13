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
    def test_autoscout24_selector_health_ratio(self) -> None:
        """Verifica que la tasa de acierto de los selectores esté por encima de un umbral saludable (TASK-016)."""
        html = _read("autoscout24_search_results.html")
        provider = AutoScout24Provider()
        provider.reset_selector_health()

        # Forzar el parseo de HTML llamando directamente a super() para activar el tracking de selectores
        super(AutoScout24Provider, provider)._parse_search_results(html, "https://www.autoscout24.de/lst")
        health = provider.get_selector_health()

        hits = sum(h["hits"] for h in health.values())
        misses = sum(h["misses"] for h in health.values())
        total = hits + misses
        assert total > 0
        ratio = hits / total
        assert ratio >= 0.1  # Al menos un selector debe hacer hit en el HTML de muestra

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