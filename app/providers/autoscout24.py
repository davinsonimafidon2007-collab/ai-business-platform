"""Provider para AutoScout24.

Implementa la lógica específica de AutoScout24:
  - ``source_name``
  - Parsing prioritario vía ``__NEXT_DATA__`` (JSON embebido, estable)
  - Fallback HTML con selectores actualizados (2026-08)
  - Configuraciones de clase para selectores y patrones de combustible

Verificado en vivo (2026-08-02): la página de listados devuelve
``article[data-testid="list-item"]`` con data-attrs y
``props.pageProps.listings`` en ``__NEXT_DATA__``.
Los selectores antiguos (``article.cld-list-item``,
``div[class*='ListItem']``) estaban rotos o devolvían ruido de UI.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleSearchResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.autoscout24.de"


class AutoScout24Provider(VehicleProvider):
    """Provider para AutoScout24."""

    _vehicle_detail_path = "/angebote/"

    _title_selector_groups = [
        (".ListItemTitle_title__sLi_x", "h2.ListItemTitle_title__sLi_x"),
        (".list-title", "h1.list-title", "h2.list-title", "h3.list-title"),
        ("h1.title", "h2.title", "h3.title", ".title h1", ".title h2"),
        ("h1", "h2", "h3"),
    ]

    _location_label_keywords = (
        "ubicación",
        "location",
        "localidad",
        "standort",
    )

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
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "autoscout24"

    def _parse_search_results(self, html: str, search_url: str) -> list[VehicleSearchResult]:
        """Parsea resultados priorizando ``__NEXT_DATA__`` (más estable)."""
        from_json = self._parse_listings_from_next_data(html)
        if from_json:
            logger.debug(
                "autoscout24: %d anuncios extraídos de __NEXT_DATA__",
                len(from_json),
            )
            return from_json

        logger.info(
            "autoscout24: __NEXT_DATA__ ausente o vacío; fallback a selectores HTML"
        )
        return super()._parse_search_results(html, search_url)

    def _parse_listings_from_next_data(self, html: str) -> list[VehicleSearchResult]:
        """Extrae listings desde el JSON embebido de Next.js."""
        match = re.search(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not match:
            return []

        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            logger.warning("autoscout24: __NEXT_DATA__ no es JSON válido: %s", exc)
            return []

        listings = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("listings")
        )
        if not isinstance(listings, list) or not listings:
            return []

        results: list[VehicleSearchResult] = []
        for item in listings:
            if not isinstance(item, dict):
                continue
            parsed = self._listing_dict_to_result(item)
            if parsed is not None:
                results.append(parsed)
        return results

    def _listing_dict_to_result(self, item: dict[str, Any]) -> VehicleSearchResult | None:
        """Mapea un objeto listing de pageProps a VehicleSearchResult."""
        external_id = str(
            item.get("id")
            or (item.get("identifier") or {}).get("crossReferenceId")
            or item.get("crossReferenceId")
            or ""
        ).strip()
        if not external_id:
            return None

        relative_url = item.get("url") or ""
        url = urljoin(f"{self._base_url}/", relative_url.lstrip("/")) if relative_url else None

        vehicle = item.get("vehicle") if isinstance(item.get("vehicle"), dict) else {}
        price_obj = item.get("price") if isinstance(item.get("price"), dict) else {}
        location_obj = item.get("location") if isinstance(item.get("location"), dict) else {}
        tracking = item.get("tracking") if isinstance(item.get("tracking"), dict) else {}
        seller = item.get("seller") if isinstance(item.get("seller"), dict) else {}

        brand = vehicle.get("make")
        model = vehicle.get("model")
        version = vehicle.get("modelVersionInput") or vehicle.get("variant")

        price_raw = price_obj.get("priceRaw")
        price: float | None
        try:
            price = float(price_raw) if price_raw is not None else None
        except (TypeError, ValueError):
            price = self._parse_price_text(str(price_obj.get("priceFormatted") or ""))

        mileage = self._parse_intish(
            tracking.get("mileage") or vehicle.get("mileageInKm")
        )
        year = self._year_from_registration(
            tracking.get("firstRegistration") or item.get("firstRegistration")
        )
        first_registration = tracking.get("firstRegistration")

        fuel_raw = vehicle.get("fuel") or tracking.get("fuelType")
        fuel_type = self._normalize_fuel(str(fuel_raw)) if fuel_raw else None

        transmission = vehicle.get("transmission")
        power_hp = self._parse_intish(vehicle.get("powerInHp") or vehicle.get("power"))
        displacement_cc = self._parse_intish(vehicle.get("engineDisplacementInCCM"))

        city = location_obj.get("city")
        zip_code = location_obj.get("zip")
        country = location_obj.get("countryCode")
        location_parts = [p for p in (zip_code, city, country) if p]
        location = " ".join(location_parts) if location_parts else None

        seller_type = seller.get("type")
        images = item.get("images") if isinstance(item.get("images"), list) else []
        images = [str(u) for u in images if u]

        return VehicleSearchResult(
            source=self.source_name,
            external_id=external_id,
            url=url,
            brand=brand,
            model=model,
            version=version,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=transmission,
            power_hp=power_hp,
            displacement_cc=displacement_cc,
            location=location,
            seller_type=seller_type,
            first_registration=first_registration,
            price=price,
            currency="EUR",
            images=images,
            description=vehicle.get("subtitle"),
            raw_data=item,
        )

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Selectores HTML de fallback (compatibles con fixtures y HTML actual)."""
        strategies = [
            'article[data-testid="list-item"]',
            "article.list-page-item",
            "article.cldt-summary-full-item",
            "article[data-guid]",
            "article[data-price]",
            "article.cld-list-item",
            "article.listing",
            "div.ListItem",
            "div[class*='ListItem']",
            "[data-listing-id]",
        ]
        for selector in strategies:
            nodes = soup.select(selector)
            if nodes:
                logger.debug(
                    "autoscout24: selector HTML %r -> %d nodos",
                    selector,
                    len(nodes),
                )
                return nodes

        logger.warning(
            "autoscout24: ninguna estrategia de selector encontró anuncios. "
            "Es probable que AutoScout24 haya cambiado su HTML — revisar selectores."
        )
        return []

    def _parse_listing_node(self, node: Any, search_url: str) -> VehicleSearchResult | None:
        """Fallback HTML: prioriza data-attrs del article actual de AS24."""
        href_candidates = [a.get("href") for a in node.select("a[href]") if a.get("href")]
        has_valid_offer_url = any("/angebote/" in href or "/offers/" in href for href in href_candidates)
        if not has_valid_offer_url and not node.get("data-guid") and not node.get("data-listing-id"):
            return None

        external_id = (
            node.get("data-guid")
            or node.get("id")
            or node.get("data-listing-id")
        )
        data_price = node.get("data-price")
        data_make = node.get("data-make")
        data_model = node.get("data-model")
        data_mileage = node.get("data-mileage")
        data_first_reg = node.get("data-first-registration")
        data_fuel = node.get("data-fuel-type")

        url = None
        if external_id:
            url = urljoin(f"{self._base_url}/", f"angebote/{external_id}")
        else:
            for anchor in node.select("a[href]"):
                href = anchor.get("href") or ""
                if "/angebote/" in href or "/offers/" in href:
                    url = self._extract_url(anchor)
                    external_id = self._extract_external_id(url)
                    break

        if not external_id and not has_valid_offer_url:
            return None
        if not external_id:
            return super()._parse_listing_node(node, search_url)
        if not url and not has_valid_offer_url:
            return None

        title = self._extract_title(node)
        brand, model = self._split_brand_model(title)
        brand = (data_make.title() if data_make else brand)
        model = (data_model.title() if data_model else model)

        try:
            price = float(data_price) if data_price is not None else self._extract_price(node)
        except (TypeError, ValueError):
            price = self._extract_price(node)

        mileage = self._parse_intish(data_mileage) or self._extract_mileage(node)
        year = self._year_from_registration(data_first_reg) or self._extract_year(node)
        fuel_type = self._normalize_fuel(str(data_fuel)) if data_fuel else self._extract_fuel(node)

        return VehicleSearchResult(
            source=self.source_name,
            external_id=str(external_id),
            url=url,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=self._extract_transmission(node),
            power_hp=self._extract_power(node),
            location=self._extract_location(node),
            first_registration=data_first_reg,
            images=self._extract_images(node),
            price=price,
            currency="EUR",
        )

    def _normalize_fuel(self, raw: str) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None
        code_map = {
            "b": "Gasolina",
            "d": "Diesel",
            "e": "Eléctrico",
            "h": "Híbrido",
            "l": "Gas",
            "c": "Gas",
        }
        if len(text) == 1 and text.lower() in code_map:
            return code_map[text.lower()]
        for pattern, label in self._fuel_patterns:
            if pattern.search(text):
                return label
        return text

    @staticmethod
    def _parse_intish(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value)
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    @staticmethod
    def _year_from_registration(value: Any) -> int | None:
        if value is None:
            return None
        text = str(value)
        match = re.search(r"(20\d{2}|19\d{2})", text)
        if match:
            return int(match.group(1))
        return None
