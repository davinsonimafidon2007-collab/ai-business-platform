"""AutoScout24 España (Task P.1b).

Reutiliza el parser de AutoScout24 DE (HTML / __NEXT_DATA__).
Solo cambia source_name y base_url (.es).
"""

from __future__ import annotations

from typing import Any

from app.providers.autoscout24 import AutoScout24Provider

BASE_URL_ES = "https://www.autoscout24.es"


class AutoScout24EsProvider(AutoScout24Provider):
    """Provider AutoScout24 para el mercado español."""

    def __init__(
        self,
        http_client: Any = None,
        base_url: str = BASE_URL_ES,
    ) -> None:
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "autoscout24_es"
