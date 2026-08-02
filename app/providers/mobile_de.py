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

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import ProviderConnectionError

logger = logging.getLogger(__name__)

# Debe coincidir con get_mobile_de_provider() en app/api/v1/dependencies.py
BASE_URL = "https://suchen.mobile.de"

_BLOCK_MARKERS = (
    "Zugriff verweigert",
    "Access denied",
    "Access Denied",
    "cf-browser-verification",
    "Just a moment",
)


class MobileDeProvider(VehicleProvider):
    """Provider para mobile.de."""

    # mobile.de no usa /vehiculo/{id}; el detalle es query-string.
    # Se overridea get_vehicle en lugar de _vehicle_detail_path.
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


    async def _download_url(self, url: str) -> str:
        """Descarga HTML; convierte 403 anti-bot en ProviderConnectionError."""
        try:
            return await super()._download_url(url)
        except Exception as exc:
            # httpx.HTTPStatusError no se traduce en ProviderHttpClient para 4xx
            status = getattr(getattr(exc, "response", None), "status_code", None)
            msg = str(exc)
            if status == 403 or "403" in msg:
                logger.error(
                    "mobile_de: HTTP 403 anti-bot (url=%s)",
                    url,
                )
                raise ProviderConnectionError(
                    "mobile.de bloqueó la petición (HTTP 403). "
                    "Configura un proxy residencial o cookies de navegador real.",
                    provider=self.source_name,
                    original_error=exc if isinstance(exc, Exception) else None,
                ) from exc
            raise

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        """Obtiene el detalle de un vehículo en mobile.de.

        Si ``external_id`` es una URL completa, se usa tal cual.
        Si es un ID numérico, se construye la URL de detalle real de mobile.de.
        """
        if external_id.startswith("http"):
            url = external_id
        else:
            # Formato real: https://suchen.mobile.de/fahrzeuge/details.html?id=123456789
            base = (self._base_url or BASE_URL).rstrip("/")
            url = f"{base}/fahrzeuge/details.html?id={external_id}"

        html = await self._download_url(url)
        self._raise_if_blocked(html, url)
        return self._parse_vehicle_detail(html, url)

    def _parse_search_results(self, html: str, search_url: str) -> list[VehicleSearchResult]:
        self._raise_if_blocked(html, search_url)
        return super()._parse_search_results(html, search_url)

    def _raise_if_blocked(self, html: str, url: str) -> None:
        """Detecta páginas de bloqueo anti-bot y lanza error explícito."""
        head = (html or "")[:4000]
        if any(marker in head for marker in _BLOCK_MARKERS):
            logger.error(
                "mobile_de: respuesta bloqueada por anti-bot (url=%s). "
                "Usar proxy residencial o sesión de navegador.",
                url,
            )
            raise ProviderConnectionError(
                "mobile.de bloqueó la petición (Access denied / anti-bot). "
                "Configura un proxy residencial o cookies de navegador real.",
                provider=self.source_name,
            )

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos.

        Orden de más específico a más genérico. Cuando se consiga HTML real
        post-bypass, validar y reordenar según el DOM vigente.
        """
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
            if nodes:
                logger.debug("mobile_de: selector %r -> %d nodos", selector, len(nodes))
                return nodes

        logger.warning(
            "mobile_de: ninguna estrategia de selector encontró anuncios. "
            "Es probable que mobile.de haya cambiado su HTML — revisar selectores."
        )
        return []
