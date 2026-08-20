"""Fixture HTML simulada de coches.net (ES_DATA_MODE=fixture).

Permite registrar un provider con nombre ``coches_net`` que devuelve
resultados simulados cuando no hay HTML real disponible.
"""

from __future__ import annotations

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult


class CochesNetHtmlFixtureProvider(VehicleProvider):
    """Provider simulado basado en HTML de coches.net."""

    @property
    def source_name(self) -> str:
        return "coches_net_html_fixture"

    def _find_listing_nodes(self, soup):  # type: ignore[override]
        return []

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        return []

    async def get_vehicle(self, external_id: str) -> VehicleDetail | None:
        return None
