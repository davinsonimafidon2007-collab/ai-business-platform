"""Provider real de Coches.net (TASK 2).

Sigue el mismo patrón que AutoScout24Provider: hereda de ``VehicleProvider``,
delega HTTP/retries/anti-bot en ``ProviderHttpClient`` y solo implementa la
lógica específica de coches.net (``source_name``, ``build_search_url`` y
``_find_listing_nodes``), más pequeños overrides de extracción justificados por
el HTML real capturado (fecha de verificación: 2026-08-20).

Verificación del selector (2026-08-20): captura real de
``https://www.coches.net/segunda-mano/`` con curl + User-Agent Chrome 124 →
HTTP 200 sin bloqueo Cloudflare desde esta red (1.47 MB). El markup real de
cada ficha es:

    <div data-ad-position="0" data-ad-id="71266436" class="mt-ListAds-item">
      <div class="mt-AnimationFadeOut mt-ListAds-item mt-CardAd mt-CardBasic">
        <div class="sui-AtomCard ...">
          <h2 class="mt-CardAd-infoHeaderTitle" data-testid="card-ad-title">
            <a class="mt-CardAd-infoHeaderTitleLink"
               href="/volkswagen-...-71210536-covo.aspx">VOLKSWAGEN Tiguan...</a>
          </h2>
          <div class="mt-CardAdPrice...">
            <p class="mt-CardAdPrice-cashAmount">26.990 €</p>
          </div>
          <ul class="mt-CardAd-attr">
            <li class="mt-CardAd-attrItem">Híbrido enchufable</li>
            <li class="mt-CardAd-attrItem">2023</li>
            <li class="mt-CardAd-attrItem">47,980 km</li>
            <li class="mt-CardAd-attrItem">245 cv</li>
            <li class="mt-CardAd-attrItem">Barcelona</li>
          </ul>
        </div>
      </div>
    </div>

La captura está guardada en ``tests/fixtures/coches_net_sample.html`` y es la
base de los tests de parsing. Observaciones de esa captura:

- **No hay <article>**: el selector ``article[data-ad-position]`` (hipótesis
  inicial de TASK 2) NO matchea nada en este HTML. El wrapper real de cada
  anuncio es ``div[data-ad-id]`` (35 ad-id únicos; 10 fichas SSR completas con
  ``mt-CardAd`` y el resto son placeholders de cliente vacíos — sin <a> — que
  se descartan en ``_parse_listing_node`` al no tener URL).
- Precio: ``26.990 €`` (punto miles, espacio no-break + €). Kilometraje en
  formato ES con **coma** (``47,980 km``), que el regex base de
  ``VehicleProvider._extract_mileage`` no cubre; año suelto como item de la
  lista ``mt-CardAd-attrItem`` (sin etiqueta "año"), que el base tampoco cubre.
  Por eso este módulo sobreescribe ``_extract_mileage`` / ``_extract_year`` /
  ``_extract_location`` de forma acotada.

Si el scraping falla (bloqueo anti-bot, HTML cambiado, timeout), propaga la
excepción — NUNCA cae a fixtures en silencio (ver TASK 1 / AUDIT.PARALLEL.1).
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import ProviderConnectionError, ProviderParsingError

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coches.net"

# Marcadores de bloqueo anti-bot (Cloudflare / WAF), mismo espíritu que
# mobile_de.py. Si aparecen en el HTML, la petición no va a ninguna parte:
# se aborta con ProviderConnectionError en vez de intentar parsear.
_BLOCK_MARKERS = (
    "cf-browser-verification",
    "Just a moment",
    "Access denied",
    "Access Denied",
)

# Edge de CloudFront de coches.net (verificación 2026-08-20): si el cliente
# anuncia ``Accept-Encoding: ...br`` sirve a veces un cuerpo *brotli*
# etiquetado como ``gzip``; httpx (sin el paquete brotli instalado) lo pasa a
# zlib y revienta con ``httpx.DecodingError``. Para coches.net se pide
# ``gzip, deflate`` (sin ``br``) y, de persistir el error, ``identity``.
_NO_BROTLI_HEADERS = {"Accept-Encoding": "gzip, deflate"}
_DECODE_RETRY_HEADERS = {"Accept-Encoding": "identity"}


class CochesNetProvider(VehicleProvider):
    """Provider para coches.net (mercado español)."""

    def __init__(self, http_client: Any = None, base_url: str = BASE_URL) -> None:
        super().__init__(http_client=http_client, base_url=base_url)

    # Combustible/tracción: añade los términos usados en el mercado ES
    # ("eléctrico", "enchufable", "híbrido" — no "hybrid" —, "dsg", "cvt"...).
    _fuel_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"benzin|petrol|gasolina", re.IGNORECASE), "Gasolina"),
        (re.compile(r"diesel", re.IGNORECASE), "Diesel"),
        (re.compile(r"el[ée]ctrico|electric|elektro", re.IGNORECASE), "Eléctrico"),
        (
            re.compile(r"hybrid|enchufable|h[ií]brido", re.IGNORECASE),
            "Híbrido",
        ),
        (re.compile(r"wasserstoff", re.IGNORECASE), "Hidrógeno"),
        (re.compile(r"lpg|cng|glp", re.IGNORECASE), "Gas"),
    ]

    _transmission_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"schaltgetriebe|manual", re.IGNORECASE), "Manual"),
        (
            re.compile(
                r"automatik|autom[áa]tic[ao]|dsg|tronic|cvt|multitronic|tiptronic",
                re.IGNORECASE,
            ),
            "Automática",
        ),
    ]

    @property
    def source_name(self) -> str:
        return "coches_net"

    def build_search_url(self, query: str, **kwargs: Any) -> str:
        if query and query.strip().startswith("http"):
            return query.strip()

        brand = (kwargs.get("brand") or "").strip()
        model = (kwargs.get("model") or "").strip()
        if not brand and query:
            parts = query.strip().split(None, 1)
            brand = parts[0]
            if not model and len(parts) > 1:
                model = parts[1]

        # coches.net: /segunda-mano/{marca}-{modelo}/
        slug = quote(f"{brand}-{model}".strip("-").lower().replace(" ", "-"))
        path = f"/segunda-mano/{slug}/" if slug else "/segunda-mano/"

        params = []
        min_price = kwargs.get("min_price") or kwargs.get("budget_min")
        max_price = kwargs.get("max_price") or kwargs.get("budget_max")
        if min_price is not None:
            params.append(f"pf={int(min_price)}")
        if max_price is not None:
            params.append(f"pt={int(max_price)}")

        url = f"{self._base_url or BASE_URL}{path}"
        if params:
            url += "?" + "&".join(params)
        return url

    # ------------------------------------------------------------------
    # Capa de transporte y bloqueo anti-bot (patrón mobile_de.py)
    # ------------------------------------------------------------------

    async def _download_url(self, url: str) -> str:
        """Descarga HTML sin anunciar ``br`` (brotli).

        El edge de CloudFront de coches.net sirve a veces un cuerpo brotli
        etiquetado como gzip cuando el cliente anuncia ``Accept-Encoding: br``
        (ver ``_NO_BROTLI_HEADERS``). ``ProviderHttpClient`` es compartido y
        sí anuncia ``br``; aquí se controla el header por petición. Si aun así
        falla el decode, se reintenta con ``identity`` y, si persiste, propaga
        la excepción (degradación explícita, nunca datos falsos).
        """
        client = await self._get_client()
        try:
            response = await client.get(url, headers=_NO_BROTLI_HEADERS)
            return response.text
        except httpx.DecodingError as exc:
            logger.warning(
                "coches_net: DecodingError en %s (%s). Reintento identity.",
                url,
                exc,
            )
            response = await client.get(url, headers=_DECODE_RETRY_HEADERS)
            return response.text

    def _raise_if_blocked(self, html: str, url: str) -> None:
        head = (html or "")[:8000]
        if any(marker in head for marker in _BLOCK_MARKERS):
            logger.error("coches_net: respuesta bloqueada por anti-bot (url=%s).", url)
            raise ProviderConnectionError(
                "coches.net bloqueó la petición (anti-bot). Configura un proxy "
                "residencial o cookies de navegador real.",
                provider=self.source_name,
            )

    def _parse_search_results(self, html: str, search_url: str) -> list[VehicleSearchResult]:
        self._raise_if_blocked(html, search_url)
        return super()._parse_search_results(html, search_url)

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        # coches.net no usa rutas /vehiculo/{id}: el id real es la URL completa
        # del anuncio (fallback de ``_extract_external_id``).
        if external_id.startswith("http"):
            url = external_id
        else:
            base = (self._base_url or BASE_URL).rstrip("/")
            url = f"{base}/{external_id}"

        html = await self._download_url(url)
        self._raise_if_blocked(html, url)
        return self._parse_vehicle_detail(html, url)

    # ------------------------------------------------------------------
    # Selectores de listado (único punto de fallo visible)
    # ------------------------------------------------------------------

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza las fichas de anuncio del listado.

        Verificado contra ``tests/fixtures/coches_net_sample.html`` (captura
        real 2026-08-20): ``div[data-ad-id]`` devuelve 35 id únicos — 10 fichas
        SSR completas con ``mt-CardAd`` y 25 placeholders vacíos de cliente que
        descarta ``_parse_listing_node`` (sin <a>).

        Si ninguna estrategia matchea (bloqueo anti-bot o cambio de HTML) se
        lanza ``ProviderParsingError``: fallo visible, nunca [] silencioso ni
        degradación a datos falsos (TASK 1 / AUDIT.PARALLEL.1).
        """
        strategies = (
            "div[data-ad-id]",
            "div[data-ad-position]",
            "div.mt-CardAd",
            "div.mt-ListAds-item",
        )
        for selector in strategies:
            nodes = soup.select(selector)
            self._track_selector(selector, bool(nodes))
            if nodes:
                deduped = self._dedupe_by_ad_id(nodes)
                if deduped:
                    logger.debug(
                        "coches_net: selector %r -> %d nodos (dedupe %d)",
                        selector,
                        len(nodes),
                        len(deduped),
                    )
                    return deduped

        raise ProviderParsingError(
            message=(
                "No se encontraron listados en coches.net. Posible bloqueo "
                "anti-bot o cambio de HTML. No se usa fallback a fixture."
            ),
            provider=self.source_name,
        )

    @staticmethod
    def _dedupe_by_ad_id(nodes: list[Any]) -> list[Any]:
        """Los wrappers ``div[data-ad-id]`` pueden repetir el mismo id
        (placeholder anidado). Se conserva el primer nodo por ``data-ad-id``."""
        seen: set[str] = set()
        out: list[Any] = []
        for node in nodes:
            key = node.get("data-ad-id")
            if key is None:
                out.append(node)
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(node)
        return out

    # ------------------------------------------------------------------
    # Overrides de extracción (formatos ES reales del fixture capturado)
    # ------------------------------------------------------------------

    def _extract_mileage(self, soup: Any) -> int | None:
        """Formato ES con coma: ``47,980 km``.

        Debe ejecutarse ANTES que el base: el regex base hace *prefix match* y
        sobre ``47,980 km`` devolvería ``980`` (se queda con el final de un
        número con separador de miles por coma). Se usa ``get_text(" ")``
        porque ``get_text()`` sin separador concatena items de listas
        (``2023`` + ``47,980 km`` → ``202347,980 km``) y rompe ``(?<!\\d)``.
        """
        text = soup.get_text(" ")
        match = re.search(
            r"(?<!\d)(\d{1,3}(?:[.,]\d{3})+)\s*km",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                return int(match.group(1).replace(".", "").replace(",", ""))
            except ValueError:
                return None
        return super()._extract_mileage(soup)

    def _extract_power(self, soup: Any) -> int | None:
        """``245 cv`` va en un ``li.mt-CardAd-attrItem`` separado.

        ``VehicleProvider._extract_power`` usa ``get_text()`` sin separador y
        concatena los items (``245 cvBarcelona``): el ``\\b`` de ``cv\\b`` deja
        de matchear. Este fallback reintenta con separador de espacio.
        """
        value = super()._extract_power(soup)
        if value is not None:
            return value
        match = re.search(
            r"(?<!\d)(\d{2,4})\s*(?:hp|cv|ch)\b",
            soup.get_text(" "),
            re.IGNORECASE,
        )
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _extract_year(self, soup: Any) -> int | None:
        """Año como item suelto: ``<li class="mt-CardAd-attrItem">2023</li>``."""
        value = super()._extract_year(soup)
        if value is not None:
            return value
        for el in soup.select(".mt-CardAd-attrItem"):
            raw = el.get_text(strip=True)
            if len(raw) == 4 and raw.isdigit():
                year = int(raw)
                if 1980 <= year <= 2100:
                    return year
        return None

    def _extract_location(self, soup: Any) -> str | None:
        """Ciudad como último item de atributos (heurística validada en el
        fixture real: "Barcelona", "Madrid" aparecen como último ``attrItem``)."""
        value = super()._extract_location(soup)
        if value:
            return value
        city: str | None = None
        fuel_words = re.compile(
            r"\b(?:híbrido|hibrido|enchufable|diesel|gasolina|benzin|petrol|"
            r"el[ée]ctrico|electric|glp|cng|lpg|hidrógeno|hidrogeno)\b",
            re.IGNORECASE,
        )
        for el in soup.select(".mt-CardAd-attrItem"):
            text = el.get_text(" ", strip=True)
            if len(text) < 2 or re.search(r"\d", text):
                continue
            low = text.lower()
            if low.endswith(("km", "cv")) or fuel_words.search(text):
                continue
            city = text
        return city
