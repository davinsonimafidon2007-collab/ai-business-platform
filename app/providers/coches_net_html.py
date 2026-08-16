"""Parser offline de listados Coches.net (HTML fixture) — P.1d.

Fixture sintético para tests; sustituir por HTML capturado real en P.1e cuando haya captura estable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult

DEFAULT_HTML = Path(__file__).resolve().parent / "fixtures" / "coches_net_list_sample.html"


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    only = re.sub(r"[^\d]", "", text)
    if not only:
        return None
    try:
        return float(only)
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    only = re.sub(r"[^\d]", "", text or "")
    return int(only) if only else None


class CochesNetHtmlFixtureProvider(VehicleProvider):
    """Listados desde HTML local; sin HTTP."""

    def __init__(
        self,
        html_path: Path | str | None = None,
        http_client: Any = None,
        base_url: str = "https://www.coches.net",
    ) -> None:
        super().__init__(http_client=http_client, base_url=base_url)
        path = Path(html_path) if html_path else DEFAULT_HTML
        self._html = path.read_text(encoding="utf-8") if path.is_file() else ""

    @property
    def source_name(self) -> str:
        return "coches_net_html_fixture"

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        return list(soup.select("article.ad-preview"))

    def _parse_articles(self) -> list[VehicleSearchResult]:
        soup = BeautifulSoup(self._html, "html.parser")
        out: list[VehicleSearchResult] = []
        for node in self._find_listing_nodes(soup):
            ext = node.get("data-ad-id") or ""
            a = node.select_one("a.ad-preview-title")
            title = (a.get_text(strip=True) if a else "") or ""
            href = a.get("href") if a else None
            price_el = node.select_one(".ad-preview-price")
            year_el = node.select_one(".ad-preview-year")
            km_el = node.select_one(".ad-preview-km")
            loc_el = node.select_one(".ad-preview-location")
            brand, model = None, None
            parts = title.split(None, 1)
            if parts:
                brand = parts[0]
                model = parts[1] if len(parts) > 1 else None
            out.append(
                VehicleSearchResult(
                    source=self.source_name,
                    external_id=str(ext),
                    url=href,
                    brand=brand,
                    model=model,
                    year=_parse_int(year_el.get_text() if year_el else ""),
                    mileage=_parse_int(km_el.get_text() if km_el else ""),
                    price=_parse_price(price_el.get_text() if price_el else ""),
                    currency="EUR",
                    location=loc_el.get_text(strip=True) if loc_el else None,
                    raw_data={"title": title},
                )
            )
        return out

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        tokens = [t for t in re.split(r"\s+", query.strip().lower()) if t]
        results = self._parse_articles()
        if not tokens:
            return results

        def ok(r: VehicleSearchResult) -> bool:
            blob = f"{r.brand or ''} {r.model or ''} {r.raw_data.get('title', '')}".lower()
            return all(t in blob for t in tokens)

        return [r for r in results if ok(r)]

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        for r in self._parse_articles():
            if r.external_id == str(external_id):
                return VehicleDetail(
                    source=self.source_name,
                    external_id=r.external_id,
                    url=r.url,
                    brand=r.brand,
                    model=r.model,
                    year=r.year,
                    mileage=r.mileage,
                    price=r.price,
                    currency=r.currency,
                    location=r.location,
                )
        return VehicleDetail(source=self.source_name, external_id=str(external_id))

    async def _download_url(self, url: str) -> str:
        raise RuntimeError("CochesNetHtmlFixtureProvider does not use HTTP")
