"""Provider para mobile.de.

Implementa únicamente la lógica específica de mobile.de:
  - ``source_name``
  - ``_find_listing_nodes`` (selectores CSS propios del HTML de mobile.de)

El resto de la lógica de parsing se hereda de ``VehicleProvider``.
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider

BASE_URL = "https://www.mobile.de"


class MobileDeProvider(VehicleProvider):
    """Provider para mobile.de.

    Soporta búsqueda por URL (la URL de resultados de búsqueda de mobile.de),
    descarga de HTML, parsing con BeautifulSoup4 + lxml y extracción de datos
    normalizados al DTO ``VehicleSearchResult``.
    """

    def __init__(
        self,
        http_client: Any = None,
        base_url: str = BASE_URL,
    ) -> None:
        """Inicializa el provider de mobile.de.

        Args:
            http_client: Cliente HTTP reutilizable. Si no se proporciona,
                se crea uno nuevo basado en ``base_url``.
            base_url: URL base de mobile.de.
        """
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "mobile_de"

    # ------------------------------------------------------------------
    # Búsqueda de nodos (específica de mobile.de)
    # ------------------------------------------------------------------

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos."""
        # Estrategia 1: article.listing
        nodes = soup.select("article.listing")
        if nodes:
            return nodes

        # Estrategia 2: div con data-listing-id
        nodes = soup.select("[data-listing-id]")
        if nodes:
            return nodes

        # Estrategia 3: div.cBox--listing
        nodes = soup.select("div.cBox--listing")
        if nodes:
            return nodes

        # Estrategia 4: div.listing
        nodes = soup.select("div.listing")
        if nodes:
            return nodes

        # Estrategia 5: div con clase que contiene "result"
        nodes = soup.select("div[class*='result']")
        if nodes:
            return nodes

        import logging
        logging.getLogger(__name__).warning(
            "mobile_de: ninguna estrategia de selector encontró anuncios. "
            "Es probable que mobile.de haya cambiado su HTML — revisar selectores."
        )
        return []

