"""Contract tests for HTML provider fixtures — TASK-015 (FASE 6).

Valida que los fixtures offline sigan cumpliendo el CONTRATO estructural que
los parsers asumen: claves del JSON embebido ``__NEXT_DATA__`` y selectores
CSS críticos. Corre offline (sin red).

Es la capa complementaria a:
- ``test_provider_html_regression.py`` — verifica el output del parseo sobre
  los fixtures.
- ``test_autoscout24_parser.py`` — unittest del parser con payloads sintéticos.

Aquí se comprueba directamente la estructura del FIXTURE contra los selectores
que el código usa. Si AS24 / mobile.de cambian su HTML y el fixture se
actualiza sin respetar el contrato, o si alguien sustituye el fixture por otro
que no encaja, estos tests fallan y avisan del drift antes de tocar red.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _soup(name: str) -> BeautifulSoup:
    return BeautifulSoup(_read(name), "html.parser")


def _next_data_html(name: str) -> str | None:
    """Contenido del script ``__NEXT_DATA__`` (misma regex que el parser)."""
    html = _read(name)
    match = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    return match.group(1) if match else None


def _next_data_listings(name: str) -> list[dict]:
    payload = json.loads(_next_data_html(name))
    return payload["props"]["pageProps"]["listings"]


class TestAutoScout24Contract:
    """El fixture de resultados cumple el contrato del parser AS24.

    El parser usa como vía primaria el JSON de ``__NEXT_DATA__``
    (``props.pageProps.listings``) y como fallback
    ``article[data-testid="list-item"]`` con data-attrs.
    """

    def test_path_primario_es_next_data(self) -> None:
        """El fixture debe conservar ``__NEXT_DATA__`` (vía primaria del parser)."""
        assert _next_data_html("autoscout24_search_results.html") is not None, (
            "Fixture sin __NEXT_DATA__: el parser pierde su vía primaria"
        )

    def test_next_data_tiene_pageprops_listings_no_vacias(self) -> None:
        listings = _next_data_listings("autoscout24_search_results.html")
        assert isinstance(listings, list) and listings, (
            "props.pageProps.listings vacío o ausente en el fixture"
        )

    def test_cada_listing_requiere_id_url_y_vehicle(self) -> None:
        for item in _next_data_listings("autoscout24_search_results.html"):
            assert item.get("id"), f"lista sin id: {item}"
            assert "/angebote/" in (item.get("url") or ""), f"url no navegable: {item}"
            vehicle = item.get("vehicle") or {}
            assert vehicle.get("make") and vehicle.get("model"), f"sin make/model: {item}"

    def test_cada_listing_requiere_precio_raw(self) -> None:
        for item in _next_data_listings("autoscout24_search_results.html"):
            price = item.get("price") or {}
            assert price.get("priceRaw") is not None, f"sin priceRaw: {item}"

    def test_fallback_html_usar_data_testid_list_item(self) -> None:
        """El fallback (``_find_listing_nodes``) usa ``article[data-testid="list-item"]``."""
        cards = _soup("autoscout24_search_results.html").select(
            'article[data-testid="list-item"]'
        )
        assert cards, "fallback: sin article[data-testid='list-item']"
        for card in cards:
            assert card.get("data-guid"), "card sin data-guid"
            assert card.get("data-price"), "card sin data-price"
            assert card.get("data-model") or card.get("data-make"), (
                "card sin data-make/data-model que el fallback lee"
            )

    def test_fixture_vacio_sigue_siendo_next_data_ok(self) -> None:
        """Un 0 resultados legítimo conserva ``listings=[]`` (no rompe la estructura)."""
        payload = json.loads(_next_data_html("autoscout24_search_empty.html"))
        assert payload["props"]["pageProps"]["listings"] == []
        assert not _soup("autoscout24_search_empty.html").select(
            'article[data-testid="list-item"]'
        )


class TestMobileDeContract:
    """El fixture de resultados cumple el contrato del parser mobile.de.

    El parser usa ``article.listing`` con ``data-listing-id`` como estrategia
    principal y luego selectores por atributo/clase.
    """

    def test_selector_principal_article_listing(self) -> None:
        cards = _soup("mobile_de_search_results.html").select("article.listing")
        assert cards, "sin article.listing"
        for card in cards:
            assert card.get("data-listing-id"), "card sin data-listing-id"

    def test_selector_secundario_data_listing_id(self) -> None:
        """``[data-listing-id]`` debe seguir funcionando como selector alternativo."""
        assert _soup("mobile_de_search_results.html").select("[data-listing-id]"), (
            "sin [data-listing-id]"
        )

    def test_cada_listado_navegable_tiene_enlace(self) -> None:
        """Las tarjetas con enlace apuntan a ``details.html?id=``; las que no
        llevan enlace son casos negativos que el parser debe ignorar."""
        cards = _soup("mobile_de_search_results.html").select("article.listing")
        navigable = [c for c in cards if c.select_one("a[href]")]
        assert navigable, "sin listados navegables"
        for card in navigable:
            href = card.select_one("a[href]").get("href")
            assert "details.html?id=" in href, f"enlace sin id de detalle: {href}"

    def test_fixture_incluye_tarjeta_sin_enlace_para_skip(self) -> None:
        """mobile.de a veces devuelve tarjetas sin enlace; deben existir en el
        fixture para que el parser verifique que las ignora (sin external_id)."""
        cards = _soup("mobile_de_search_results.html").select("article.listing")
        without_link = [
            c for c in cards if not c.select_one("a[href]") and c.get("data-listing-id")
        ]
        assert without_link, "perdido el caso de tarjeta sin enlace (skip parser)"

    def test_mileage_presente_en_el_fixture(self) -> None:
        """El kilometraje aparece al menos en una tarjeta (extracción opcional)."""
        cards = _soup("mobile_de_search_results.html").select("article.listing")
        assert any(card.select_one(".mileage") for card in cards), (
            "ningún listado con .mileage: el parser pierde el kilometraje"
        )

    def test_fixture_vacio_no_tiene_listados(self) -> None:
        assert not _soup("mobile_de_search_empty.html").select(
            "article.listing[data-listing-id]"
        )