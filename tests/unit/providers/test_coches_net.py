"""TASK 2 — CochesNetProvider: URL de búsqueda, selectores reales y registry.

Los tests de parsing usan el HTML **real** de coches.net capturado manualmente
(``tests/fixtures/coches_net_sample.html``, curl + UA Chrome 124, 2026-08-20),
no un fixture sintético. Si el HTML cambia y el fixture se regenera, estos
tests deben fallar de forma visible (selectores obsoletos → revisar).
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from app.core.config import settings
from app.providers.coches_net import BASE_URL, CochesNetProvider
from app.providers.exceptions import ProviderConnectionError, ProviderParsingError
from app.providers.registry import ProviderRegistry

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "coches_net_sample.html"


def setup_function() -> None:
    ProviderRegistry.clear()


def teardown_function() -> None:
    ProviderRegistry.clear()


def _fixture_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# source_name / base_url
# ---------------------------------------------------------------------------


def test_source_name_and_base_url() -> None:
    provider = CochesNetProvider()
    assert provider.source_name == "coches_net"
    assert "coches.net" in (provider._base_url or BASE_URL)


# ---------------------------------------------------------------------------
# _download_url: transporte específico (sin brotli por el edge de CloudFront)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeClient:
    def __init__(self, text: str = "<html><body>ok</body></html>") -> None:
        self.text = text
        self.calls: list[dict | None] = []
        self.fail_on_first = False

    async def get(self, url: str, headers: dict | None = None, **kwargs: object) -> _FakeResponse:
        self.calls.append(headers)
        if self.fail_on_first:
            self.fail_on_first = False
            raise httpx.DecodingError("incorrect header check")
        return _FakeResponse(self.text)


@pytest.mark.asyncio
async def test_download_url_requests_without_brotli(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = CochesNetProvider(http_client=None)
    fake = _FakeClient(text="<html><body>ok</body></html>")

    async def _fake_get_client() -> _FakeClient:
        return fake

    monkeypatch.setattr(provider, "_get_client", _fake_get_client)
    html = await provider._download_url("https://www.coches.net/segunda-mano/")
    assert html == "<html><body>ok</body></html>"
    assert len(fake.calls) == 1
    assert fake.calls[0] == {"Accept-Encoding": "gzip, deflate"}


@pytest.mark.asyncio
async def test_download_url_retries_identity_on_decoding_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CochesNetProvider(http_client=None)
    fake = _FakeClient(text="<html><body>retry-ok</body></html>")
    fake.fail_on_first = True

    async def _fake_get_client() -> _FakeClient:
        return fake

    monkeypatch.setattr(provider, "_get_client", _fake_get_client)
    html = await provider._download_url("https://www.coches.net/segunda-mano/")
    assert html == "<html><body>retry-ok</body></html>"
    assert len(fake.calls) == 2
    assert fake.calls[0] == {"Accept-Encoding": "gzip, deflate"}
    assert fake.calls[1] == {"Accept-Encoding": "identity"}


# ---------------------------------------------------------------------------
# build_search_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "kwargs", "expected"),
    [
        ("seat", {}, f"{BASE_URL}/segunda-mano/seat/"),
        ("seat ibiza", {}, f"{BASE_URL}/segunda-mano/seat-ibiza/"),
        ("SEAT Ibiza", {}, f"{BASE_URL}/segunda-mano/seat-ibiza/"),
        ("bmw", {"model": "serie 3"}, f"{BASE_URL}/segunda-mano/bmw-serie-3/"),
        ("", {}, f"{BASE_URL}/segunda-mano/"),
        (
            "",
            {"brand": "land rover", "model": "discovery"},
            f"{BASE_URL}/segunda-mano/land-rover-discovery/",
        ),
        ("", {"model": "ibiza"}, f"{BASE_URL}/segunda-mano/ibiza/"),
        (
            "seat ibiza",
            {"min_price": 8000, "max_price": 15000},
            f"{BASE_URL}/segunda-mano/seat-ibiza/?pf=8000&pt=15000",
        ),
        (
            "seat ibiza",
            {"budget_min": 8000, "budget_max": 15000},
            f"{BASE_URL}/segunda-mano/seat-ibiza/?pf=8000&pt=15000",
        ),
        ("citroen c4", {}, f"{BASE_URL}/segunda-mano/citroen-c4/"),
    ],
)
def test_build_search_url(query: str, kwargs: dict, expected: str) -> None:
    provider = CochesNetProvider()
    assert provider.build_search_url(query, **kwargs) == expected


def test_build_search_url_passthrough_http() -> None:
    provider = CochesNetProvider()
    url = "https://www.coches.net/segunda-mano/seat-ibiza/?pf=5000#filtros"
    assert provider.build_search_url(url) == url
    assert provider.build_search_url(f"  {url}  ") == url


# ---------------------------------------------------------------------------
# _find_listing_nodes contra el HTML REAL capturado
# ---------------------------------------------------------------------------


def test_find_listing_nodes_against_real_fixture() -> None:
    provider = CochesNetProvider()
    soup = BeautifulSoup(_fixture_html(), "lxml")
    nodes = provider._find_listing_nodes(soup)

    assert nodes, "El HTML real capturado debe matchear al menos una ficha"
    ids = [n.get("data-ad-id") for n in nodes]
    assert all(ids), "todos los nodos deben traer data-ad-id (selección primaria)"
    # En la captura de 2026-08-20 hay 35 ad-id únicos y 10 fichas SSR completas.
    assert len(ids) >= 10
    assert len(set(ids)) == len(ids), "no debe haber anuncios duplicados"


def test_find_listing_nodes_no_match_raises() -> None:
    provider = CochesNetProvider()
    soup = BeautifulSoup(
        "<html><body><div>página sin anuncios ni selectores conocidos</div></body></html>",
        "lxml",
    )
    with pytest.raises(ProviderParsingError) as exc_info:
        provider._find_listing_nodes(soup)
    assert exc_info.value.provider == "coches_net"
    assert "coches.net" in str(exc_info.value)


def test_blocked_html_raises_provider_connection_error() -> None:
    provider = CochesNetProvider()
    blocked = (
        "<html><head><title>Just a moment...</title></head>"
        "<body>cf-browser-verification</body></html>"
    )
    with pytest.raises(ProviderConnectionError) as exc_info:
        provider._parse_search_results(blocked, f"{BASE_URL}/segunda-mano/")
    assert exc_info.value.provider == "coches_net"


# ---------------------------------------------------------------------------
# search() end-to-end contra el HTML real (offline, _download_url mockeado)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_parses_real_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = CochesNetProvider(http_client=None)
    html = _fixture_html()

    async def _fake_download(url: str) -> str:
        return html

    monkeypatch.setattr(provider, "_download_url", _fake_download)
    results = await provider.search(f"{BASE_URL}/segunda-mano/")

    rich = [r for r in results if r.price]
    assert len(rich) >= 1, "el HTML real debe producir al menos una ficha con precio"

    for r in rich:
        assert r.source == "coches_net"
        assert r.url and r.url.startswith("http")
        assert r.external_id
        assert r.brand
        assert r.price > 100

    # Formatos ES reales del fixture: km con coma, año suelto, ciudad.
    assert any(r.mileage for r in rich)
    assert any(r.year for r in rich)
    assert any(r.location for r in rich)
    # Dedupe: ningún anuncio repetido en los resultados.
    assert len({r.external_id for r in rich}) == len(rich)


# ---------------------------------------------------------------------------
# Registry: ES_DATA_MODE=live registra coches_net real (no fixture)
# ---------------------------------------------------------------------------


def _live_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "es_data_mode", "live")
    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_mobile_de", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)


def test_registry_live_mode_registers_coches_net(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _live_mode(monkeypatch)
    ProviderRegistry.ensure_default_providers()

    names = ProviderRegistry.list_providers()
    assert "coches_net" in names
    provider = ProviderRegistry.get("coches_net")
    assert provider.source_name == "coches_net"
    assert isinstance(provider, CochesNetProvider)
    # live: los fixtures ES NUNCA se registran (TASK 1).
    for fixture in (
        "es_market_fixture",
        "coches_net_fixture",
        "coches_net_html_fixture",
    ):
        assert fixture not in names


def test_registry_fixture_mode_does_not_register_coches_net_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En modo fixture, si el provider real está desactivado
    (``enable_coches_net=False``), no se registra — cae a fixtures.

    Nota (fusión con origin/main, TASK 4 / AUD-005): ``ES_DATA_MODE`` no es
    el único interruptor de coches_net real. ``enable_coches_net`` es
    independiente y con su default (True) el scraper real se usa también
    en modo fixture — ver ``test_default_providers_registered`` en
    test_registry_es_mode.py. Este test cubre el caso en que se desactiva
    explícitamente.
    """
    monkeypatch.setattr(settings, "es_data_mode", "fixture")
    monkeypatch.setattr(settings, "default_import_cost_profile", "SPAIN")
    monkeypatch.setattr(settings, "enable_mobile_de", False)
    monkeypatch.setattr(settings, "enable_autoscout24_es", False)
    monkeypatch.setattr(settings, "enable_es_market_fixture", True)
    monkeypatch.setattr(settings, "enable_coches_net", False)

    ProviderRegistry.ensure_default_providers()
    assert "coches_net" not in ProviderRegistry.list_providers()
    assert "es_market_fixture" in ProviderRegistry.list_providers()


def test_registry_live_mode_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _live_mode(monkeypatch)
    ProviderRegistry.ensure_default_providers()
    ProviderRegistry.ensure_default_providers()
    assert sum(1 for n in ProviderRegistry.list_providers() if n == "coches_net") == 1
