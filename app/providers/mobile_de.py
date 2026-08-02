"""Provider for mobile.de vehicle search.

Notes (2026):
  - Datacenter IPs frequently receive HTTP 403 "Access denied".
  - When a 403 is detected we raise ProviderConnectionError so the
    orchestrator can fall back or retry via residential proxy.
  - Selectors are ordered by specificity and ready for when access works.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

try:
    from app.providers.base import BaseProvider, ProviderConnectionError, ProviderParseError
    from app.schemas.vehicle import VehicleSearchResult
except Exception:  # pragma: no cover
    from dataclasses import dataclass

    @dataclass
    class VehicleSearchResult:
        source: str
        title: str
        price: float | None = None
        currency: str | None = None
        year: int | None = None
        mileage_km: int | None = None
        fuel_type: str | None = None
        transmission: str | None = None
        location: str | None = None
        url: str | None = None
        image_url: str | None = None
        external_id: str | None = None
        raw: object | None = None

    class ProviderConnectionError(Exception):
        pass

    class ProviderParseError(Exception):
        pass

    class BaseProvider:
        name = ""
        base_url = ""

        async def _fetch(self, url: str) -> str:
            import httpx

            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text

logger = logging.getLogger(__name__)

_BASE = "https://www.mobile.de"
_SEARCH_PATH = "/fahrzeuge/search.html"

_CARD_SELECTORS = (
    "article.vehicle-data",
    "div.cBox-body--resultitem",
    "div.result-item",
    "article[data-testid='result-listing']",
    "div[class*='resultItem']",
)


class MobileDeProvider(BaseProvider):
    """Scrapes mobile.de public search results."""

    name = "mobile_de"
    base_url = _BASE

    def _build_search_url(self, query: str, max_price: int | None, country: str) -> str:
        params: dict[str, str] = {
            "isSearchRequest": "true",
            "s": "Car",
            "vc": "Car",
        }
        if query:
            params["q"] = query
        if max_price is not None and max_price > 0:
            params["p"] = f":{int(max_price)}"
        # country bias (DE default)
        if country and country.upper() == "DE":
            params["cn"] = "DE"
        return f"{_BASE}{_SEARCH_PATH}?{urlencode(params)}"

    async def search(
        self,
        query: str,
        max_price: int | None = None,
        country: str = "DE",
        limit: int = 20,
    ) -> list[VehicleSearchResult]:
        url = self._build_search_url(query, max_price, country)
        try:
            html = await self._fetch(url)
        except Exception as exc:
            # Surface 403 / anti-bot clearly
            msg = str(exc)
            if "403" in msg or "Access denied" in msg or "Forbidden" in msg:
                raise ProviderConnectionError(
                    "mobile.de returned 403 Access denied (anti-bot). "
                    "Use a residential proxy or rotate identity."
                ) from exc
            raise ProviderConnectionError(f"mobile.de fetch failed: {exc}") from exc

        # Extra safety: detect soft-block pages that return 200 with block HTML
        if "Access denied" in html or "Request blocked" in html or "captcha" in html.lower():
            raise ProviderConnectionError(
                "mobile.de anti-bot page detected in HTML body. "
                "Residential proxy required."
            )

        try:
            results = self._parse_html(html, limit=limit)
        except Exception as exc:
            raise ProviderParseError(f"mobile.de parse failed: {exc}") from exc

        return results

    def _parse_html(self, html: str, limit: int = 20) -> list[VehicleSearchResult]:
        soup = BeautifulSoup(html, "lxml")

        cards: list[Tag] = []
        for sel in _CARD_SELECTORS:
            found = soup.select(sel)
            if found:
                cards = found
                break

        if not cards:
            logger.warning("mobile.de: no listing cards found with current selectors")
            return []

        results: list[VehicleSearchResult] = []
        for card in cards[:limit]:
            try:
                item = self._parse_card(card)
                if item is not None:
                    results.append(item)
            except Exception as exc:
                logger.debug("mobile.de card parse skip: %s", exc)
                continue
        return results

    def _parse_card(self, card: Tag) -> VehicleSearchResult | None:
        # Title + URL
        link = (
            card.select_one("a[href*='/fahrzeuge/details.html']")
            or card.select_one("a[data-testid='result-listing-title']")
            or card.select_one("a.vehicle-data-link")
            or card.select_one("a[href]")
        )
        if not link:
            return None

        href = link.get("href") or ""
        if not href:
            return None
        detail_url = urljoin(_BASE, href)
        title = link.get_text(strip=True) or (card.get("title") or "").strip()
        if not title:
            return None

        # External ID from URL query or path
        listing_id = ""
        m = re.search(r"[?&]id=(\d+)", detail_url)
        if m:
            listing_id = m.group(1)
        else:
            m2 = re.search(r"/(\d+)(?:\.html)?(?:\?|$)", detail_url)
            if m2:
                listing_id = m2.group(1)
        if not listing_id:
            listing_id = detail_url.rstrip("/").split("/")[-1][:64]

        # Price
        price = None
        price_el = (
            card.select_one("[data-testid='price-label']")
            or card.select_one(".price-block")
            or card.select_one("[class*='price']")
        )
        if price_el:
            price = self._parse_price(price_el.get_text(" ", strip=True))

        # Year / mileage from detail line
        detail_text = card.get_text(" ", strip=True)
        year = self._parse_year(detail_text)
        mileage = self._parse_mileage(detail_text)

        # Fuel / transmission (best-effort)
        fuel = None
        transmission = None
        lower = detail_text.lower()
        for kw in ("diesel", "benzin", "elektro", "hybrid", "gas", "lpg"):
            if kw in lower:
                fuel = "Petrol" if kw == "benzin" else kw.capitalize()
                break
        for kw in ("automatik", "automatic", "schaltgetriebe", "manual"):
            if kw in lower:
                transmission = "Automatic" if "auto" in kw else "Manual"
                break

        # Location
        loc_el = (
            card.select_one("[data-testid='seller-address']")
            or card.select_one("[class*='location']")
            or card.select_one("[class*='seller']")
        )
        location = loc_el.get_text(strip=True) if loc_el else None

        # Image
        img = card.select_one("img[src], img[data-src]")
        image_url = None
        if img:
            image_url = img.get("src") or img.get("data-src")

        return VehicleSearchResult(
            external_id=listing_id,
            source=self.name,
            title=title,
            price=price,
            currency="EUR",
            year=year,
            mileage_km=mileage,
            fuel_type=fuel,
            transmission=transmission,
            location=location,
            url=detail_url,
            image_url=image_url,
            raw=None,
        )

    @staticmethod
    def _parse_price(text: str) -> float | None:
        if not text:
            return None
        cleaned = (
            text.replace("€", "")
            .replace("EUR", "")
            .replace(".-", "")
            .replace(",-", "")
            .replace(".", "")
            .replace(" ", "")
            .replace("\xa0", "")
            .strip()
        )
        cleaned = re.sub(r"[^\d,]", "", cleaned)
        if "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            val = float(cleaned)
            return val if val > 0 else None
        except ValueError:
            return None

    @staticmethod
    def _parse_year(text: str) -> int | None:
        m = re.search(r"\b(19[8-9]\d|20[0-2]\d)\b", text)
        return int(m.group(1)) if m else None

    @staticmethod
    def _parse_mileage(text: str) -> int | None:
        m = re.search(r"([\d.\s]+)\s*(?:km|KM)", text)
        if not m:
            return None
        raw = m.group(1).replace(".", "").replace(" ", "").replace("\xa0", "")
        try:
            return int(raw)
        except ValueError:
            return None
