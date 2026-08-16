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
        """URL de listados AS24 España (cy=E, path sin modelo)."""
        if query and query.strip().startswith("http"):
            return query.strip()

        from urllib.parse import quote, urlencode

        brand = (kwargs.get("brand") or "").strip()
        model = (kwargs.get("model") or "").strip()

        if not brand and query:
            parts = query.strip().split(None, 1)
            brand = parts[0]
            if not model and len(parts) > 1:
                model = parts[1]

        path = "/lst"
        if brand:
            path += f"/{quote(brand.lower().replace(' ', '-'))}"

        params: dict[str, str] = {
            "atype": "C",
            "cy": "E",
            "desc": "0",
            "sort": "standard",
            "source": "listpage_search-mask",
            "ustate": "N,U",
        }

        if model:
            params["q"] = model

        mapping = {
            "min_price": "pricefrom",
            "budget_min": "pricefrom",
            "max_price": "priceto",
            "budget_max": "priceto",
            "min_year": "fregfrom",
            "max_year": "fregto",
            "max_mileage": "kmto",
            "min_mileage": "kmfrom",
        }
        for key, param in mapping.items():
            value = kwargs.get(key)
            if value is not None:
                params[param] = str(int(value)) if isinstance(value, float) else str(value)

        fuel_map = {
            "gasolina": "B", "petrol": "B", "benzin": "B",
            "diesel": "D",
            "eléctrico": "E", "electrico": "E", "electric": "E",
            "híbrido": "2", "hibrido": "2", "hybrid": "2",
        }
        fuel = (kwargs.get("fuel_type") or "").strip().lower()
        if fuel in fuel_map:
            params["fuel"] = fuel_map[fuel]

        transmission = (kwargs.get("transmission") or "").strip().lower()
        if transmission in {"manual", "schaltgetriebe"}:
            params["gear"] = "M"
        elif transmission in {"automática", "automatica", "automatic", "automatik"}:
            params["gear"] = "A"

        return f"{self._base_url or BASE_URL_ES}{path}?{urlencode(params)}"
