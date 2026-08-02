"""Provider for AutoScout24 vehicle search.

Primary strategy (2024–2026 AS24 list pages):
  1. Extract listings from the Next.js hydration payload ``__NEXT_DATA__``
     → ``props.pageProps.listings`` (most reliable).
  2. Fallback: parse current list-item DOM selectors used by AS24.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
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
        raw: Any | None = None

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

_BASE = "https://www.autoscout24.com"
_SEARCH_PATH = "/lst"

# Current AS24 list-item selectors (ordered by specificity).
_CARD_SELECTORS = (
    'article[data-testid="list-item"]',
    'article[data-testid="list-page-item"]',
    "article.cldt-summary-full-item",
    "article[data-guid]",
)


class AutoScout24Provider(BaseProvider):
    """Scrapes AutoScout24 public search results."""

    name = "autoscout24"
    base_url = _BASE

    def _build_search_url(self, query: str, max_price: int | None, country: str) -> str:
        params: dict[str, str] = {
            "atype": "C",
            "cy": country.upper() if country else "D",
            "desc": "0",
            "sort": "standard",
            "ustate": "N,U",
        }
        if query:
            params["q"] = query
        if max_price is not None and max_price > 0:
            params["pricefrom"] = "0"
            params["priceto"] = str(int(max_price))
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
            raise ProviderConnectionError(f"AutoScout24 fetch failed: {exc}") from exc

        try:
            results = self._parse_html(html, limit=limit)
        except Exception as exc:
            raise ProviderParseError(f"AutoScout24 parse failed: {exc}") from exc

        return results

    def _parse_html(self, html: str, limit: int = 20) -> list[VehicleSearchResult]:
        soup = BeautifulSoup(html, "lxml")

        # --- Strategy 1: Next.js JSON payload (most reliable) ---
        results = self._parse_next_data(soup, limit=limit)
        if results:
            return results

        # --- Strategy 2: Current list-item DOM ---
        cards: list[Tag] = []
        for sel in _CARD_SELECTORS:
            found = soup.select(sel)
            if found:
                cards = found
                break

        if not cards:
            logger.warning("AutoScout24: no listing cards found with current selectors")
            return []

        results = []
        for card in cards[:limit]:
            try:
                item = self._parse_card(card)
                if item is not None:
                    results.append(item)
            except Exception as exc:
                logger.debug("AS24 card parse skip: %s", exc)
                continue
        return results

    def _parse_next_data(self, soup: BeautifulSoup, limit: int) -> list[VehicleSearchResult]:
        """Extract listings from ``<script id="__NEXT_DATA__">`` if present."""
        script = soup.find("script", id="__NEXT_DATA__")
        if script is None or not script.string:
            return []

        try:
            payload = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            return []

        listings = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("listings")
        )
        if not isinstance(listings, list) or not listings:
            return []

        results: list[VehicleSearchResult] = []
        for raw in listings[:limit]:
            try:
                item = self._listing_from_json(raw)
                if item is not None:
                    results.append(item)
            except Exception as exc:
                logger.debug("AS24 JSON listing skip: %s", exc)
                continue
        return results

    def _listing_from_json(self, raw: dict[str, Any]) -> VehicleSearchResult | None:
        """Map a single AS24 Next.js listing object to VehicleSearchResult."""
        vehicle = raw.get("vehicle") or {}
        price_info = raw.get("price") or {}
        location = raw.get("location") or {}
        seller = raw.get("seller") or {}

        # ID
        listing_id = str(raw.get("id") or raw.get("listingId") or "").strip()
        if not listing_id:
            return None

        # Title
        make = (vehicle.get("make") or "").strip()
        model = (vehicle.get("model") or "").strip()
        title = f"{make} {model}".strip() or (raw.get("title") or "").strip()
        if not title:
            return None

        # Price (EUR)
        price_val = price_info.get("price") or price_info.get("public") or raw.get("price")
        try:
            price = float(price_val) if price_val is not None else None
        except (TypeError, ValueError):
            price = None
        if price is not None and price <= 0:
            price = None

        # Year
        year = None
        first_reg = vehicle.get("firstRegistration") or vehicle.get("firstRegistrationDate")
        if isinstance(first_reg, str) and len(first_reg) >= 4:
            try:
                year = int(first_reg[:4])
            except ValueError:
                pass
        if year is None and vehicle.get("year"):
            try:
                year = int(vehicle["year"])
            except (TypeError, ValueError):
                pass

        # Mileage
        mileage = None
        km_raw = vehicle.get("mileage") or vehicle.get("mileageInKm")
        if isinstance(km_raw, dict):
            km_raw = km_raw.get("value") or km_raw.get("raw")
        try:
            if km_raw is not None:
                mileage = int(str(km_raw).replace(".", "").replace(",", "").replace(" ", ""))
        except (TypeError, ValueError):
            pass

        # Fuel / transmission
        fuel = (vehicle.get("fuel") or vehicle.get("fuelType") or "").strip() or None
        transmission = (vehicle.get("transmission") or vehicle.get("gearbox") or "").strip() or None

        # Location
        city = (location.get("city") or "").strip()
        zip_code = (location.get("zip") or location.get("zipCode") or "").strip()
        loc_str = ", ".join(p for p in (city, zip_code) if p) or None

        # URL
        relative = raw.get("url") or raw.get("detailsUrl") or f"/angebote/{listing_id}"
        if isinstance(relative, str) and relative.startswith("http"):
            detail_url = relative
        else:
            detail_url = urljoin(_BASE, str(relative))

        # Image
        images = raw.get("images") or raw.get("imageUrls") or []
        image_url = None
        if images and isinstance(images, list):
            first = images[0]
            if isinstance(first, str):
                image_url = first
            elif isinstance(first, dict):
                image_url = first.get("url") or first.get("src")

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
            location=loc_str,
            url=detail_url,
            image_url=image_url,
            raw={"seller": seller.get("type") if isinstance(seller, dict) else None},
        )

    def _parse_card(self, card: Tag) -> VehicleSearchResult | None:
        """Parse a single list-item article from the DOM."""
        # ID
        listing_id = (
            card.get("data-guid")
            or card.get("data-id")
            or card.get("data-listing-id")
            or ""
        )
        listing_id = str(listing_id).strip()

        # Title
        title_el = (
            card.select_one('[data-testid="list-item-title"]')
            or card.select_one("h2")
            or card.select_one(".ListItemTitle")
            or card.select_one("a[href*='/angebote/']")
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        # URL — prefer the offer link, not dealer profile
        href = None
        for a in card.select("a[href]"):
            h = a.get("href") or ""
            if "/angebote/" in h or "/offers/" in h:
                href = h
                break
        if not href and title_el and title_el.name == "a":
            href = title_el.get("href")
        if not href:
            # last resort: first link that is not a dealer profile
            for a in card.select("a[href]"):
                h = a.get("href") or ""
                if h and "haendler" not in h and "dealer" not in h:
                    href = h
                    break
        if not href:
            return None
        detail_url = urljoin(_BASE, href)

        if not listing_id:
            # try to extract from URL
            m = re.search(r"/angebote/[^/]*?-([a-f0-9]+)", detail_url, re.I)
            if m:
                listing_id = m.group(1)
            else:
                listing_id = detail_url.rstrip("/").split("/")[-1][:64]

        # Price
        price = None
        price_el = (
            card.select_one('[data-testid="list-item-price"]')
            or card.select_one(".Price_price__")
            or card.select_one("[class*='price']")
        )
        if price_el:
            price = self._parse_price(price_el.get_text(" ", strip=True))

        # Year / mileage from subtitle or detail lines
        year = None
        mileage = None
        detail_text = ""
        for sel in (
            '[data-testid="list-item-subtitle"]',
            ".ListItem_subtitle__",
            "[class*='VehicleDetail']",
            "span[class*='detail']",
        ):
            el = card.select_one(sel)
            if el:
                detail_text += " " + el.get_text(" ", strip=True)

        # Also collect all short text nodes that look like "2020" or "45.000 km"
        for el in card.select("span, li, p"):
            t = el.get_text(strip=True)
            if t and len(t) < 40:
                detail_text += " " + t

        year = self._parse_year(detail_text) or year
        mileage = self._parse_mileage(detail_text) or mileage

        # Fuel / transmission (best-effort from text)
        fuel = None
        transmission = None
        lower = detail_text.lower()
        for kw in ("diesel", "benzin", "elektro", "hybrid", "gas", "lpg", "cng"):
            if kw in lower:
                fuel = kw.capitalize() if kw != "benzin" else "Petrol"
                break
        for kw in ("automatik", "automatic", "schaltgetriebe", "manual"):
            if kw in lower:
                transmission = "Automatic" if "auto" in kw else "Manual"
                break

        # Location
        loc_el = (
            card.select_one('[data-testid="list-item-location"]')
            or card.select_one("[class*='location']")
            or card.select_one("[class*='Location']")
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
        # "€ 12.450" or "12450 €" or "12.450,-"
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
        # keep only digits and optional decimal comma
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
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _parse_mileage(text: str) -> int | None:
        m = re.search(r"([\d.\s]+)\s*(?:km|KM)", text)
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "").replace("\xa0", "")
            try:
                return int(raw)
            except ValueError:
                return None
        return None
