"""TASK 4 — Providers España reales.

Cubre:
- AUD-005: el scraper REAL de coches.net se registra de verdad (antes solo
  existía bajo TYPE_CHECKING y era inalcanzable en runtime).
- Regla anti-mezcla: con el provider real activo no se auto-registra su
  fixture equivalente, para no mezclar anuncios reales y simulados.
- AUD-031: todos los providers etiquetan la moneda del precio.
- AUD-033: los providers de fixtures se declaran simulados.
- AUD-030: el escaneo de texto libre se acota al contenido principal.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.core.config import settings
from app.providers.coches_net import CochesNetProvider
from app.providers.coches_net_fixture import CochesNetFixtureProvider
from app.providers.es_market_fixture import EsMarketFixtureProvider
from app.providers.registry import ProviderRegistry


@pytest.fixture(autouse=True)
def clean_registry() -> None:
    ProviderRegistry.clear()
    yield
    ProviderRegistry.clear()


@pytest.fixture
def spain_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_mobile_de", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_fixture", False)
    monkeypatch.setattr(settings, "enable_coches_net_html_fixture", False)


class TestRealCochesNetRegistration:
    def test_real_provider_is_registered_by_default(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AUD-005: el provider real ya no es código muerto."""
        monkeypatch.setattr(settings, "enable_coches_net", True)
        ProviderRegistry.ensure_default_providers()

        assert "coches_net" in ProviderRegistry.list_providers()
        provider = ProviderRegistry.get("coches_net")
        assert isinstance(provider, CochesNetProvider)
        assert provider.is_simulated is False

    def test_real_provider_can_be_disabled(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "enable_coches_net", False)
        ProviderRegistry.ensure_default_providers()

        assert "coches_net" not in ProviderRegistry.list_providers()

    def test_registration_is_idempotent(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "enable_coches_net", True)
        ProviderRegistry.ensure_default_providers()
        ProviderRegistry.ensure_default_providers()

        assert ProviderRegistry.list_providers().count("coches_net") == 1

    def test_registration_does_not_perform_http(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Registrar el provider no debe abrir conexiones (solo construir)."""
        monkeypatch.setattr(settings, "enable_coches_net", True)

        async def _fail(*args: object, **kwargs: object) -> None:  # pragma: no cover
            raise AssertionError("el registro no debe hacer HTTP")

        monkeypatch.setattr(CochesNetProvider, "search", _fail, raising=False)
        ProviderRegistry.ensure_default_providers()
        assert "coches_net" in ProviderRegistry.list_providers()


class TestRealAndFixtureDoNotMix:
    def test_real_provider_suppresses_fixture_auto_registration(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Con el real activo, el fixture de la misma fuente no se auto-registra."""
        monkeypatch.setattr(settings, "enable_coches_net", True)
        ProviderRegistry.ensure_default_providers()

        providers = ProviderRegistry.list_providers()
        assert "coches_net" in providers
        assert "coches_net_fixture" not in providers

    def test_fixture_auto_registers_when_real_is_off(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sin el real (modo offline), el fixture ES sigue disponible."""
        monkeypatch.setattr(settings, "enable_coches_net", False)
        ProviderRegistry.ensure_default_providers()

        providers = ProviderRegistry.list_providers()
        assert "coches_net_fixture" in providers
        assert "coches_net" not in providers

    def test_explicit_fixture_flag_still_wins(
        self, spain_profile: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El flag explícito permite forzar el fixture aunque el real esté activo."""
        monkeypatch.setattr(settings, "enable_coches_net", True)
        monkeypatch.setattr(settings, "enable_coches_net_fixture", True)
        ProviderRegistry.ensure_default_providers()

        providers = ProviderRegistry.list_providers()
        assert "coches_net" in providers
        assert "coches_net_fixture" in providers


class TestSimulatedFlag:
    def test_fixture_providers_declare_themselves_simulated(self) -> None:
        assert EsMarketFixtureProvider().is_simulated is True
        assert CochesNetFixtureProvider().is_simulated is True

    def test_real_provider_is_not_simulated(self) -> None:
        assert CochesNetProvider().is_simulated is False


class TestCurrencyTagging:
    """AUD-031: un precio sin moneda es un dato silenciosamente ambiguo."""

    def test_default_currency_is_eur(self) -> None:
        assert CochesNetProvider().default_currency == "EUR"

    def test_listing_parse_tags_currency(self) -> None:
        html = """
        <article data-ad-position="1">
          <a href="https://www.coches.net/bmw-320d-12345678/"></a>
          <h2>BMW 320d</h2>
          <span class="price">18.500 €</span>
          <span>95.000 km</span>
        </article>
        """
        node = BeautifulSoup(html, "lxml").select_one("article")
        result = CochesNetProvider()._parse_listing_node(node, "https://www.coches.net/")

        assert result is not None
        assert result.price == 18500.0
        assert result.currency == "EUR"

    def test_currency_is_none_without_price(self) -> None:
        """Sin precio no se inventa moneda."""
        html = """
        <article data-ad-position="1">
          <a href="https://www.coches.net/bmw-320d-12345678/"></a>
          <h2>BMW 320d</h2>
        </article>
        """
        node = BeautifulSoup(html, "lxml").select_one("article")
        result = CochesNetProvider()._parse_listing_node(node, "https://www.coches.net/")

        assert result is not None
        assert result.price is None
        assert result.currency is None


class TestSimulatedComparablesExcluded:
    """Un precio de mercado calculado con fixtures alimentaría un ROI falso."""

    def test_auto_selection_excludes_simulated_providers(self) -> None:
        from app.services.comparable_market_estimator import (
            resolve_comparable_provider_names,
        )

        names = resolve_comparable_provider_names(
            ["autoscout24", "coches_net", "es_market_fixture"],
            simulated_names={"es_market_fixture"},
        )
        assert names == ["autoscout24", "coches_net"]

    def test_explicit_request_can_still_use_simulated(self) -> None:
        from app.services.comparable_market_estimator import (
            resolve_comparable_provider_names,
        )

        names = resolve_comparable_provider_names(
            ["autoscout24", "es_market_fixture"],
            request_names=["es_market_fixture"],
            simulated_names={"es_market_fixture"},
        )
        assert names == ["es_market_fixture"]

    def test_settings_csv_can_still_use_simulated(self) -> None:
        from app.services.comparable_market_estimator import (
            resolve_comparable_provider_names,
        )

        names = resolve_comparable_provider_names(
            ["autoscout24", "es_market_fixture"],
            settings_csv="es_market_fixture",
            simulated_names={"es_market_fixture"},
        )
        assert names == ["es_market_fixture"]

    def test_no_simulated_providers_keeps_previous_behaviour(self) -> None:
        from app.services.comparable_market_estimator import (
            resolve_comparable_provider_names,
        )

        names = resolve_comparable_provider_names(["autoscout24", "coches_net"])
        assert names == ["autoscout24", "coches_net"]


class TestMainContentScoping:
    """AUD-030: no tomar el precio/km de un anuncio relacionado."""

    _PAGE = """
    <html><body>
      <main>
        <h1>BMW 320d</h1>
        <div class="price">18.500 €</div>
        <div>95.000 km</div>
      </main>
      <aside id="similares">
        <div class="price">9.900 €</div>
        <div>250.000 km</div>
      </aside>
    </body></html>
    """

    def test_price_comes_from_main_not_from_sidebar(self) -> None:
        soup = BeautifulSoup(self._PAGE, "lxml")
        # Se elimina el selector de clase para forzar el escaneo de texto,
        # que es justamente el camino que antes leía toda la página.
        main_only = CochesNetProvider()._main_content_scope(soup)
        assert "9.900" not in main_only.get_text()
        assert "18.500" in main_only.get_text()

    def test_mileage_comes_from_main_not_from_sidebar(self) -> None:
        soup = BeautifulSoup(self._PAGE, "lxml")
        mileage = CochesNetProvider()._extract_mileage(soup)
        assert mileage == 95000

    def test_listing_node_is_not_rescoped(self) -> None:
        """Un nodo de anuncio (sin <body>) se usa tal cual."""
        node = BeautifulSoup(
            '<article><div class="price">18.500 €</div></article>', "lxml"
        ).select_one("article")
        assert CochesNetProvider()._main_content_scope(node) is node

    def test_page_without_main_container_falls_back_to_full_document(self) -> None:
        soup = BeautifulSoup(
            "<html><body><div class='x'>18.500 €</div></body></html>", "lxml"
        )
        scoped = CochesNetProvider()._main_content_scope(soup)
        assert "18.500" in scoped.get_text()
