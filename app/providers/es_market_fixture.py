"""Provider offline de mercado ES (Task P.1a).

No hace HTTP. Carga listings desde JSON de fixtures y filtra por query
(brand/model en texto libre, case-insensitive).

Pensado para:
  - alimentar ComparableMarketEstimator con precios destino ES
  - tests deterministas sin red
  - sustituible por coches.net / AS24-ES en P.1b sin cambiar el estimador

NOTE (AUDIT.PARALLEL.1): Este provider es un fixture offline intencional.
Los providers ES live (coches.net, etc.) NO están implementados porque
requieren scraping de sitios con anti-bot agresivo. El pipeline de
"comparables españoles" usa datos de fixture para estimación de mercado.
Para datos live, usar AutoScout24 (que sí tiene scraping funcional).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "es_market_sample.json"
)


class EsMarketFixtureProvider(VehicleProvider):
    """Comparables de mercado español desde fixture local."""

    def __init__(
        self,
        fixture_path: Path | str | None = None,
        http_client: Any = None,
        base_url: str = "https://fixture.es",
    ) -> None:
        super().__init__(http_client=http_client, base_url=base_url)
        path = Path(fixture_path) if fixture_path else DEFAULT_FIXTURE_PATH
        self._listings: list[dict[str, Any]] = self._load(path)

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            logger.warning("ES market fixture missing: %s", path)
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        listings = data.get("listings") if isinstance(data, dict) else data
        if not isinstance(listings, list):
            return []
        return [x for x in listings if isinstance(x, dict)]

    @property
    def source_name(self) -> str:
        return "es_market_fixture"

    @property
    def is_simulated(self) -> bool:
        """Datos de fixture, no del sitio real (TASK 4 / AUD-033)."""
        return True

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        # No HTML real: la API search/get_vehicle está sobreescrita.
        return []

    def _tokens(self, query: str) -> list[str]:
        return [t for t in re.split(r"\s+", query.strip().lower()) if t]

    def _matches(self, row: dict[str, Any], tokens: list[str]) -> bool:
        if not tokens:
            return True
        blob = " ".join(
            str(row.get(k) or "")
            for k in ("brand", "model", "version", "location")
        ).lower()
        return all(tok in blob for tok in tokens)

    def _to_search_result(self, row: dict[str, Any]) -> VehicleSearchResult:
        return VehicleSearchResult(
            source=self.source_name,
            external_id=str(row.get("external_id") or ""),
            url=row.get("url"),
            brand=row.get("brand"),
            model=row.get("model"),
            version=row.get("version"),
            year=row.get("year"),
            mileage=row.get("mileage"),
            fuel_type=row.get("fuel_type"),
            transmission=row.get("transmission"),
            location=row.get("location"),
            seller_type=row.get("seller_type"),
            price=float(row["price"]) if row.get("price") is not None else None,
            currency=row.get("currency") or "EUR",
            raw_data=dict(row),
        )

    def _to_detail(self, row: dict[str, Any]) -> VehicleDetail:
        return VehicleDetail(
            source=self.source_name,
            external_id=str(row.get("external_id") or ""),
            url=row.get("url"),
            brand=row.get("brand"),
            model=row.get("model"),
            version=row.get("version"),
            year=row.get("year"),
            mileage=row.get("mileage"),
            fuel_type=row.get("fuel_type"),
            transmission=row.get("transmission"),
            location=row.get("location"),
            seller_type=row.get("seller_type"),
            price=float(row["price"]) if row.get("price") is not None else None,
            currency=row.get("currency") or "EUR",
            description=row.get("description"),
            raw_data=dict(row),
        )

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Filtra fixtures por tokens de query (ej. 'BMW 320')."""
        tokens = self._tokens(query)
        out = [
            self._to_search_result(row)
            for row in self._listings
            if self._matches(row, tokens)
        ]
        logger.debug(
            "es_market_fixture search query=%r tokens=%s count=%d",
            query,
            tokens,
            len(out),
        )
        return out

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        for row in self._listings:
            if str(row.get("external_id")) == str(external_id):
                return self._to_detail(row)
        # Detalle mínimo si no existe (tests / robustez)
        return VehicleDetail(
            source=self.source_name,
            external_id=str(external_id),
            url=None,
            brand=None,
            model=None,
            price=None,
        )

    async def _download_url(self, url: str) -> str:
        raise RuntimeError(
            "EsMarketFixtureProvider does not use HTTP; search/get_vehicle are offline"
        )
