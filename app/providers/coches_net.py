"""Provider real de Coches.net (TASK 2).

Sigue el mismo patrón que AutoScout24Provider: hereda de VehicleProvider,
delega HTTP/retries/anti-bot en ProviderHttpClient, y solo implementa el
parsing específico de coches.net.

Si el scraping falla (bloqueo anti-bot, HTML cambiado, timeout), propaga la
excepción — NUNCA cae a fixtures en silencio (ver TASK 1 / AUDIT.PARALLEL.1).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.exceptions import ProviderConnectionError, ProviderParsingError

BASE_URL = "https://www.coches.net"


class CochesNetProvider(VehicleProvider):
    """Provider para coches.net (mercado español)."""

    def __init__(self, http_client: Any = None, base_url: str = BASE_URL) -> None:
        super().__init__(http_client=http_client, base_url=base_url)

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

        slug = quote(f"{brand}-{model}".strip("-").lower().replace(" ", "-"))
        path = f"/segunda-mano/{slug}/" if slug else "/segunda-mano/"

        params = []
        min_price = kwargs.get("min_price") or kwargs.get("budget_min")
        max_price = kwargs.get("max_price") or kwargs.get("budget_max")
        if min_price is not None:
            params.append(f"pf={int(min_price)}")
        if max_price is not None:
            params.append(f"pt={int(max_price)}")

        url = f"{self.base_url}{path}"
        if params:
            url += "?" + "&".join(params)
        return url

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        nodes = soup.select("article[data-ad-position], div.mt-CardAd")
        if not nodes:
            raise ProviderParsingError(
                message=(
                    "No se encontraron listados en coches.net. Posible bloqueo "
                    "anti-bot o cambio de HTML. No se usa fallback a fixture."
                ),
                provider=self.source_name,
            )
        return nodes
