"""Provider para mobile.de.

Implementa la lógica específica de mobile.de:
  - ``source_name``
  - ``_find_listing_nodes`` (selectores CSS propios del HTML de mobile.de)
  - URL de detalle correcta (details.html?id=...)
  - base_url alineada con el DI (suchen.mobile.de)

El resto del parsing se hereda de ``VehicleProvider``.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail

# Debe coincidir con get_mobile_de_provider() en app/api/v1/dependencies.py
BASE_URL = "https://suchen.mobile.de"


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
        return self._parse_vehicle_detail(html, url)

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos."""
        nodes = soup.select("article.listing")
        if nodes:
            return nodes

        nodes = soup.select("[data-listing-id]")
        if nodes:
            return nodes

        nodes = soup.select("div.cBox--listing")
        if nodes:
            return nodes

        nodes = soup.select("div.listing")
        if nodes:
            return nodes

        # Catch-all amplio: solo como último recurso (puede traer ruido)
        nodes = soup.select("div[class*='result-item'], div[class*='ResultItem']")
        if nodes:
            return nodes

        import logging

        logging.getLogger(__name__).warning(
            "mobile_de: ninguna estrategia de selector encontró anuncios. "
            "Es probable que mobile.de haya cambiado su HTML — revisar selectores."
        )
        return []

