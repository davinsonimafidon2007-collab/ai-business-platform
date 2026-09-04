"""Provider para mobile.de.

Implementa la lógica específica de mobile.de:
  - ``source_name``
  - ``_find_listing_nodes`` (selectores CSS propios del HTML de mobile.de)
  - URL de detalle correcta (details.html?id=...)
  - base_url alineada con el DI (suchen.mobile.de)
  - Detección de bloqueos anti-bot (403 / Access denied)

Nota (verificación 2026-08-02): peticiones desde IPs de datacenter
reciben sistemáticamente 403 «Zugriff verweigert / Access denied».
En producción hace falta proxy residencial / sesión con cookies de
navegador real. Los selectores se mantienen y se ampliarán cuando se
obtenga HTML real tras el bypass.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import ProviderConnectionError, ProviderParsingError

logger = logging.getLogger(__name__)

# En la base histórica del proyecto, mobile.de usa www.mobile.de.
# Las búsquedas reales en producción pueden apuntar a suchen.mobile.de
# si se fuerza desde las dependencias de API.
BASE_URL = "https://www.mobile.de"

_BLOCK_MARKERS = (
    "Zugriff verweigert",
    "Access denied",
    "Access Denied",
    "cf-browser-verification",
    "Just a moment",
)


class MobileDeProvider(VehicleProvider):
    """Provider para mobile.de."""

    _vehicle_detail_path = "/fahrzeuge/details.html?id="

    def __init__(
        self,
        http_client: Any = None,
        base_url: str = BASE_URL,
    ) -> None:
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "mobile_de"

    def build_search_url(self, query: str, **kwargs: Any) -> str:
        """Construye (o valida) la URL de búsqueda para mobile.de.

        Bug real encontrado probando una búsqueda en vivo con Playwright: a
        diferencia de AutoScout24Provider (que sí sobrescribe ``search()``
        para convertir un término libre en una URL válida — ver su propio
        comentario sobre el mismo problema), ``MobileDeProvider`` nunca lo
        hizo. ``VehicleProvider.search()`` base pasa el ``query`` tal cual a
        ``_download_url``; con un término libre como "BMW Serie 3" eso
        produce literalmente ``https://suchen.mobile.de/BMW Serie 3`` — una
        URL inválida con espacios sin codificar, que Playwright rechaza con
        "Protocol error (Page.navigate): Cannot navigate to invalid URL".

        A diferencia de AutoScout24 (``/lst/<marca>``, texto libre), mobile.de
        exige IDs numéricos de marca/modelo de su propia taxonomía interna
        (``makeModelVariant1.makeId=...``) para filtrar por texto — no hay
        forma verificable de mapear "BMW Serie 3" a esos IDs sin acceso
        estable al formulario real de mobile.de (bloqueado por su propio
        anti-bot al intentar inspeccionarlo). Inventar un mapeo sin verificar
        arriesga devolver resultados de la marca/modelo equivocados
        silenciosamente, peor que no soportar la búsqueda.

        Si ``query`` ya es una URL completa se respeta tal cual (mismo
        contrato que AutoScout24Provider). Si no, se declara explícitamente
        no soportado en vez de construir una URL rota o adivinada.
        """
        if query and query.strip().startswith("http"):
            return query.strip()
        raise ProviderParsingError(
            "mobile_de: búsqueda por texto libre no soportada todavía — "
            "mobile.de requiere IDs de marca/modelo de su propia taxonomía "
            "(no hay un parámetro de texto libre equivalente al '?q=' de "
            "AutoScout24). Pasa una URL de resultados de mobile.de completa "
            "si quieres usar este provider mientras tanto.",
            provider=self.source_name,
        )

    async def search(self, query: str, **kwargs: Any) -> list[VehicleSearchResult]:
        """Busca en mobile.de aceptando solo URL completa (ver build_search_url)."""
        search_url = self.build_search_url(query, **kwargs)
        return await super().search(search_url, **kwargs)

    async def _download_url(self, url: str) -> str:
        """Descarga HTML; convierte 403 anti-bot en ProviderConnectionError."""
        try:
            return await super()._download_url(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                logger.error("mobile_de: HTTP 403 anti-bot (url=%s)", url)
                raise ProviderConnectionError(
                    "mobile.de bloqueó la petición (HTTP 403). "
                    "Configura un proxy residencial o cookies de navegador real.",
                    provider=self.source_name,
                    original_error=exc,
                ) from exc
            raise
        except httpx.RequestError as exc:
            logger.error("mobile_de: request error (url=%s): %s", url, exc)
            raise ProviderConnectionError(
                f"mobile.de: error de red: {exc}",
                provider=self.source_name,
                original_error=exc,
            ) from exc

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        if external_id.startswith("http"):
            url = external_id
        else:
            base = (self._base_url or BASE_URL).rstrip("/")
            url = f"{base}/fahrzeuge/details.html?id={external_id}"

        html = await self._download_url(url)
        self._raise_if_blocked(html, url)
        return self._parse_vehicle_detail(html, url)

    def _parse_search_results(self, html: str, search_url: str) -> list[VehicleSearchResult]:
        self._raise_if_blocked(html, search_url)
        return super()._parse_search_results(html, search_url)

    def _raise_if_blocked(self, html: str, url: str) -> None:
        head = (html or "")[:4000]
        if any(marker in head for marker in _BLOCK_MARKERS):
            logger.error(
                "mobile_de: respuesta bloqueada por anti-bot (url=%s).",
                url,
            )
            raise ProviderConnectionError(
                "mobile.de bloqueó la petición (Access denied / anti-bot). "
                "Configura un proxy residencial o cookies de navegador real.",
                provider=self.source_name,
            )

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        strategies = [
            "article.listing",
            "article[data-listing-id]",
            "[data-listing-id]",
            "div.cBox--listing",
            "div.result-item",
            "div.listing",
            "div[class*='result-item']",
            "div[class*='ResultItem']",
            "div[class*='Listing']",
        ]
        for selector in strategies:
            nodes = soup.select(selector)
            self._track_selector(selector, bool(nodes))
            if nodes:
                logger.debug("mobile_de: selector %r -> %d nodos", selector, len(nodes))
                return nodes

        logger.warning(
            "mobile_de: ninguna estrategia de selector encontró anuncios. "
            "Es probable que mobile.de haya cambiado su HTML — revisar selectores."
        )
        return []
