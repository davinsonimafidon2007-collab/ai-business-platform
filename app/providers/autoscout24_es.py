"""AutoScout24 España (Task P.1b).

Reutiliza el parser de AutoScout24 DE (HTML / __NEXT_DATA__).
Solo cambia source_name, base_url (.es) y country code (E).
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

    def build_search_url(self, query: str, **kwargs: Any) -> str:
        """URL de listados AS24 España (cy=E) — delega lógica común al padre."""
        # Reusa el builder del padre pero forzando cy=E y base ES
        url = super().build_search_url(query, **kwargs)
        # super() genera cy=D por defecto; corregir a E para España
        if "cy=D" in url:
            url = url.replace("cy=D", "cy=E")
        elif "cy=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}cy=E"
        # Asegurar base ES si el padre usó DE por error
        if self._base_url and self._base_url in url:
            return url
        # Si query era URL absoluta ya se retornó; si no, reescribir host a ES
        return url.replace("https://www.autoscout24.de", self._base_url or BASE_URL_ES)
