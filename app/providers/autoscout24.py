"""Provider para AutoScout24.

Implementa únicamente la lógica específica de AutoScout24:
  - ``source_name``
  - ``_find_listing_nodes`` (selectores CSS propios del HTML de AutoScout24)
  - Configuraciones de clase para personalizar selectores y patrones

El resto de la lógica de parsing se hereda de ``VehicleProvider``.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider

BASE_URL = "https://www.autoscout24.de"


class AutoScout24Provider(VehicleProvider):
    """Provider para AutoScout24.

    Soporta búsqueda por URL (la URL de resultados de búsqueda de AutoScout24),
    descarga de HTML, parsing con BeautifulSoup4 + lxml y extracción de datos
    normalizados al DTO ``VehicleSearchResult``.
    """

    # AutoScout24 usa "/angebote/" en lugar de "/vehiculo/"
    _vehicle_detail_path = "/angebote/"

    # AutoScout24 tiene un selector específico ".list-title" como primera opción
    _title_selector_groups = [
        (".list-title", "h1.list-title", "h2.list-title", "h3.list-title"),
        ("h1.title", "h2.title", "h3.title", ".title h1", ".title h2"),
        ("h1", "h2", "h3"),
    ]

    # AutoScout24 usa "standort" como palabra clave de ubicación en alemán
    _location_label_keywords = (
        "ubicación", "location", "localidad", "standort",
    )

    # AutoScout24 incluye variantes en inglés: "electric", "hydrogen", "autogas"
    _fuel_patterns = [
        (re.compile(r"benzin|petrol|gasolina", re.IGNORECASE), "Gasolina"),
        (re.compile(r"diesel", re.IGNORECASE), "Diesel"),
        (re.compile(r"elektro|electric", re.IGNORECASE), "Eléctrico"),
        (re.compile(r"hybrid", re.IGNORECASE), "Híbrido"),
        (re.compile(r"wasserstoff|hydrogen", re.IGNORECASE), "Hidrógeno"),
        (re.compile(r"lpg|cng|autogas", re.IGNORECASE), "Gas"),
    ]

    def __init__(
        self,
        http_client: Any = None,
        base_url: str = BASE_URL,
    ) -> None:
        """Inicializa el provider de AutoScout24.

        Args:
            http_client: Cliente HTTP reutilizable. Si no se proporciona,
                se crea uno nuevo basado en ``base_url``.
            base_url: URL base de AutoScout24.
        """
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "autoscout24"

    # ------------------------------------------------------------------
    # Búsqueda de nodos (específica de AutoScout24)
    # ------------------------------------------------------------------

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos."""
        # Estrategia 1: article.cld-list-item (AutoScout24 moderno)
        nodes = soup.select("article.cld-list-item")
        if nodes:
            return nodes

        # Estrategia 2: article.listing (compatible con mobile.de style)
        nodes = soup.select("article.listing")
        if nodes:
            return nodes

        # Estrategia 3: div con data-listing-id
        nodes = soup.select("[data-listing-id]")
        if nodes:
            return nodes

        # Estrategia 4: div con clase que contiene "ListItem"
        nodes = soup.select("div[class*='ListItem']")
        if nodes:
            return nodes

        # Estrategia 5: div con clase que contiene "result"
        nodes = soup.select("div[class*='result']")
        if nodes:
            return nodes

        return []

