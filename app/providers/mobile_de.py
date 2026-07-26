"""Provider para mobile.de.

Implementa búsqueda por URL, descarga de HTML, parsing y extracción
de datos utilizando BeautifulSoup4 + lxml.

Toda la lógica de parsing está encapsulada dentro de este módulo.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from app.providers.base import VehicleProvider
from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import ProviderParsingError

BASE_URL = "https://www.mobile.de"

# Mapeo de palabras clave a tipos de combustible
_FUEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"benzin|petrol", re.IGNORECASE), "Gasolina"),
    (re.compile(r"diesel", re.IGNORECASE), "Diesel"),
    (re.compile(r"elektro", re.IGNORECASE), "Eléctrico"),
    (re.compile(r"hybrid", re.IGNORECASE), "Híbrido"),
    (re.compile(r"wasserstoff", re.IGNORECASE), "Hidrógeno"),
    (re.compile(r"lpg|cng", re.IGNORECASE), "Gas"),
]

# Mapeo de palabras clave a tipos de transmisión
_TRANSMISSION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"schaltgetriebe|manual", re.IGNORECASE), "Manual"),
    (re.compile(r"automatik|automática|automático", re.IGNORECASE), "Automática"),
]


class MobileDeProvider(VehicleProvider):
    """Provider para mobile.de.

    Soporta búsqueda por URL (la URL de resultados de búsqueda de mobile.de),
    descarga de HTML, parsing con BeautifulSoup4 + lxml y extracción de datos
    normalizados al DTO ``VehicleSearchResult``.
    """

    def __init__(
        self,
        http_client: Any = None,
        base_url: str = BASE_URL,
    ) -> None:
        """Inicializa el provider de mobile.de.

        Args:
            http_client: Cliente HTTP reutilizable. Si no se proporciona,
                se crea uno nuevo basado en ``base_url``.
            base_url: URL base de mobile.de.
        """
        super().__init__(http_client=http_client, base_url=base_url)

    @property
    def source_name(self) -> str:
        return "mobile_de"

    # ------------------------------------------------------------------
    # Búsqueda pública
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Busca vehículos en mobile.de a partir de una URL de búsqueda.

        El ``query`` debe ser una URL de resultados de búsqueda de mobile.de,
        por ejemplo::

            https://www.mobile.de/es/carisma/gebrauchtwagen.html?...

        Returns:
            Lista de resultados normalizados como ``VehicleSearchResult``.
        """
        html = await self._download_url(query)
        return self._parse_search_results(html, query)

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        """Obtiene la información detallada de un vehículo por su ID externo.

        Args:
            external_id: ID del vehículo en mobile.de (o URL completa).

        Returns:
            ``VehicleDetail`` con la información completa del vehículo.
        """
        if external_id.startswith("http"):
            url = external_id
        else:
            url = f"{BASE_URL}/vehiculo/{external_id}"

        html = await self._download_url(url)
        return self._parse_vehicle_detail(html, url)

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        """Normaliza datos crudos de mobile.de a un DTO.

        El ``raw_data`` puede contener una clave especial ``_type`` con valor
        ``"detail"`` para devolver un ``VehicleDetail`` o cualquier otro valor
        (por defecto ``"search"``) para devolver un ``VehicleSearchResult``.
        """
        is_detail = raw_data.get("_type", "search") == "detail"
        common = self._build_dto_fields(raw_data, source="mobile_de")
        if is_detail:
            return VehicleDetail(**common)
        return VehicleSearchResult(**common)

    # ------------------------------------------------------------------
    # Descarga de HTML
    # ------------------------------------------------------------------

    async def _download_url(self, url: str) -> str:
        """Descarga el HTML de una URL utilizando el cliente HTTP."""
        client = await self._get_client()
        response = await client.get(url)
        return response.text

    # ------------------------------------------------------------------
    # Parsing de resultados de búsqueda
    # ------------------------------------------------------------------

    def _parse_search_results(self, html: str, search_url: str) -> list[VehicleSearchResult]:
        """Parsea el HTML de una página de resultados de búsqueda.

        Extrae cada anuncio de vehículo y lo convierte en un
        ``VehicleSearchResult``.
        """
        soup = BeautifulSoup(html, "lxml")
        results: list[VehicleSearchResult] = []

        listing_nodes = self._find_listing_nodes(soup)

        for node in listing_nodes:
            try:
                result = self._parse_listing_node(node, search_url)
            except ProviderParsingError:
                continue
            if result is not None:
                results.append(result)

        return results

    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos."""
        # Estrategia 1: article.listing
        nodes = soup.select("article.listing")
        if nodes:
            return nodes

        # Estrategia 2: div con data-listing-id
        nodes = soup.select("[data-listing-id]")
        if nodes:
            return nodes

        # Estrategia 3: div.cBox--listing
        nodes = soup.select("div.cBox--listing")
        if nodes:
            return nodes

        # Estrategia 4: div.listing
        nodes = soup.select("div.listing")
        if nodes:
            return nodes

        # Estrategia 5: div con clase que contiene "result"
        nodes = soup.select("div[class*='result']")
        if nodes:
            return nodes

        return []

    def _parse_listing_node(self, node: Any, search_url: str) -> VehicleSearchResult | None:
        """Parsea un nodo individual de anuncio y devuelve un DTO."""
        # --- URL y external_id ---
        link_tag = node.select_one("a")
        url = self._extract_url(link_tag)
        external_id = self._extract_external_id(url)
        if not external_id:
            return None

        # --- Imágenes ---
        images = self._extract_images(node)

        # --- Título (marca + modelo) ---
        title = self._extract_title(node)
        brand, model = self._split_brand_model(title)

        # --- Precio ---
        price = self._extract_price(node)

        # --- Kilometraje ---
        mileage = self._extract_mileage(node)

        # --- Año ---
        year = self._extract_year(node)

        # --- Combustible ---
        fuel_type = self._extract_fuel(node)

        # --- Transmisión ---
        transmission = self._extract_transmission(node)

        # --- Potencia ---
        power_hp = self._extract_power(node)

        # --- Ubicación ---
        location = self._extract_location(node)

        return VehicleSearchResult(
            source=self.source_name,
            external_id=external_id,
            url=url,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=transmission,
            power_hp=power_hp,
            location=location,
            images=images,
        )

    # ------------------------------------------------------------------
    # Parsing de detalle de vehículo
    # ------------------------------------------------------------------

    def _parse_vehicle_detail(self, html: str, url: str) -> VehicleDetail:
        """Parsea el HTML de una página de detalle de vehículo."""
        soup = BeautifulSoup(html, "lxml")

        # --- URL y external_id ---
        external_id = self._extract_external_id(url)

        # --- Título ---
        title = self._extract_title(soup)
        brand, model = self._split_brand_model(title)

        # --- Precio ---
        price = self._extract_price(soup)

        # --- Kilometraje ---
        mileage = self._extract_mileage(soup)

        # --- Año ---
        year = self._extract_year(soup)

        # --- Combustible ---
        fuel_type = self._extract_fuel(soup)

        # --- Transmisión ---
        transmission = self._extract_transmission(soup)

        # --- Potencia ---
        power_hp = self._extract_power(soup)

        # --- Ubicación ---
        location = self._extract_location(soup)

        # --- Imágenes ---
        images = self._extract_images(soup)

        # --- Descripción ---
        description = self._extract_description(soup)

        return VehicleDetail(
            source=self.source_name,
            external_id=external_id,
            url=url,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=transmission,
            power_hp=power_hp,
            location=location,
            images=images,
            description=description,
        )

    # ------------------------------------------------------------------
    # Métodos de extracción (reutilizables entre búsqueda y detalle)
    # ------------------------------------------------------------------

    def _extract_url(self, tag: Any | None) -> str | None:
        """Extrae la URL canónica de un enlace."""
        if tag is None:
            return None
        href = tag.get("href")
        if not href:
            return None
        href = str(href).strip()
        if href.startswith("http"):
            return href
        if href.startswith("//"):
            return f"https:{href}"
        if href.startswith("/"):
            return f"{BASE_URL}{href}"
        return href

    def _extract_external_id(self, url: str | None) -> str | None:
        """Extrae el ID externo del vehículo de una URL de mobile.de."""
        if not url:
            return None
        # mobile.de URLs suelen terminar con el ID: /vehiculo/12345678
        # o contener /a/12345678, o -12345678 al final del path
        match = re.search(r"[-/](\d{4,})(?:/|$)", url)
        if match:
            return match.group(1)
        # Fallback: usar la URL completa como ID
        return url

    def _extract_images(self, soup: Any) -> list[str]:
        """Extrae las URLs de las imágenes principales del anuncio."""
        images: list[str] = []

        # Estrategia 1: data attributes con URLs de imágenes
        for img in soup.select("[data-image-src], [data-src], img[data-lazy]"):
            src = img.get("data-image-src") or img.get("data-src") or img.get("data-lazy")
            if src and str(src).strip():
                images.append(self._normalize_image_url(str(src)))

        # Estrategia 2: <img> con src
        if not images:
            for img in soup.select("img[src]"):
                src = img.get("src")
                if src and str(src).strip():
                    images.append(self._normalize_image_url(str(src)))

        # Deduplicar manteniendo el orden
        seen: set[str] = set()
        unique: list[str] = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique.append(img)
        return unique

    def _normalize_image_url(self, url: str) -> str:
        """Normaliza una URL de imagen."""
        url = url.strip()
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return f"{BASE_URL}{url}"
        return url

    def _extract_title(self, soup: Any) -> str | None:
        """Extrae el título del anuncio (marca + modelo)."""
        # Estrategia 1: h1, h2, h3 con clase "title"
        for selector in ("h1.title", "h2.title", "h3.title", ".title h1", ".title h2"):
            tag = soup.select_one(selector)
            if tag:
                text = tag.get_text(strip=True)
                if text:
                    return text

        # Estrategia 2: h1, h2, h3 directamente
        for level in ("h1", "h2", "h3"):
            tag = soup.select_one(level)
            if tag:
                text = tag.get_text(strip=True)
                if text:
                    return text

        # Estrategia 3: clase con "title" o "name"
        tag = soup.select_one(".title, .name, [data-test='title']")
        if tag:
            text = tag.get_text(strip=True)
            if text:
                return text

        return None

    def _split_brand_model(self, title: str | None) -> tuple[str | None, str | None]:
        """Separa marca y modelo del título del anuncio."""
        if not title:
            return None, None

        title = title.strip()

        # Los títulos de mobile.de suelen ser: "Marca Modelo Versión"
        # Ej: "BMW Serie 3 (F30) 320d"
        parts = title.split()
        if len(parts) >= 2:
            brand = parts[0]
            model = " ".join(parts[1:])
            return brand, model
        elif len(parts) == 1:
            return parts[0], None
        return None, None

    def _extract_price(self, soup: Any) -> float | None:
        """Extrae el precio del vehículo."""
        # Estrategia 1: data-price attribute (valor numérico directo)
        tag = soup.select_one("[data-price]")
        if tag:
            data_price = tag.get("data-price")
            if data_price:
                try:
                    return float(data_price)
                except (ValueError, TypeError):
                    pass
            price = self._parse_price_text(tag.get_text(strip=True))
            if price is not None:
                return price

        # Estrategia 2: selectores de clase
        for selector in (".price", "[data-test='price']"):
            tag = soup.select_one(selector)
            if tag:
                price = self._parse_price_text(tag.get_text(strip=True))
                if price is not None:
                    return price

        # Estrategia 3: buscar texto con € o EUR en todo el HTML
        text = soup.get_text()
        price = self._parse_price_text(text)
        if price is not None:
            return price

        return None

    def _parse_price_text(self, text: str) -> float | None:
        """Parsea un texto de precio y devuelve el valor numérico."""
        if not text:
            return None
        # Buscar patrones como "12.345 €", "12.345,- €", "12345 EUR"
        match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)(?:,-)?\s*(?:€|EUR|eur)", text)
        if match:
            raw = match.group(1)
            # Normalizar: eliminar puntos de miles, reemplazar coma decimal
            raw = raw.replace(".", "").replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                return None
        # También intentar sin símbolo de moneda
        match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*€", text)
        if match:
            raw = match.group(1).replace(".", "").replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                return None
        return None

    def _extract_mileage(self, soup: Any) -> int | None:
        """Extrae el kilometraje del vehículo."""
        text = soup.get_text()
        # Patrón: "123.456 km" o "123.456 Km" o "123456 km"
        # Usa negative lookbehind para evitar coincidencias parciales
        match = re.search(r"(?<!\d)(\d{1,3}(?:\.\d{3})*|\d{4,})\s*km", text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(".", "")
            try:
                return int(raw)
            except ValueError:
                return None
        # También intentar con "kilómetros"
        match = re.search(r"(?<!\d)(\d{1,3}(?:\.\d{3})*|\d{4,})\s*kilómetros", text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(".", "")
            try:
                return int(raw)
            except ValueError:
                return None
        return None

    def _extract_year(self, soup: Any) -> int | None:
        """Extrae el año de registro del vehículo."""
        text = soup.get_text()
        # Patrón: "01/2020" como año de primera matriculación
        match = re.search(r"(?:0[1-9]|1[0-2])/(20\d{2})", text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        # Patrón: "1ª matriculación: 2020" o "primer registro 2020"
        match = re.search(r"(?:matriculaci[oó]n|registro|primera)[^\d]*(\d{4})", text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2100:
                return year
        # Patrón: año de fabricación "año 2020"
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            year = int(match.group(1))
            if 1990 <= year <= 2100:
                return year
        return None

    def _extract_fuel(self, soup: Any) -> str | None:
        """Extrae el tipo de combustible."""
        text = soup.get_text()
        for pattern, fuel in _FUEL_PATTERNS:
            if pattern.search(text):
                return fuel
        return None

    def _extract_transmission(self, soup: Any) -> str | None:
        """Extrae el tipo de transmisión."""
        text = soup.get_text()
        for pattern, trans in _TRANSMISSION_PATTERNS:
            if pattern.search(text):
                return trans
        return None

    def _extract_power(self, soup: Any) -> int | None:
        """Extrae la potencia en caballos (hp)."""
        text = soup.get_text()
        # Patrón: "150 hp" o "150 HP" o "150cv"
        match = re.search(r"(\d{2,4})\s*(?:hp|cv|ch)", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _extract_location(self, soup: Any) -> str | None:
        """Extrae la ubicación del vehículo."""
        # Estrategia 1: data attributes
        for selector in ("[data-location]", ".location", "[data-test='location']"):
            tag = soup.select_one(selector)
            if tag:
                text = tag.get_text(strip=True)
                if text:
                    return text

        # Estrategia 2: buscar el valor asociado a una etiqueta de ubicación
        for label_span in soup.select(".label"):
            label_text = label_span.get_text(strip=True).lower()
            if any(kw in label_text for kw in ("ubicación", "location", "localidad", "ort")):
                value_span = label_span.find_next_sibling(".value")
                if value_span:
                    text = value_span.get_text(strip=True)
                    if text:
                        return text

        # Estrategia 3: buscar texto con localidad típica (ciudad + código postal)
        text = soup.get_text()
        match = re.search(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\d{5}\b",
            text,
        )
        if match:
            return match.group(1).strip()

        return None

    def _extract_description(self, soup: Any) -> str | None:
        """Extrae la descripción del vehículo."""
        for selector in (".description", "[data-test='description']", ".details", ".content"):
            tag = soup.select_one(selector)
            if tag:
                text = tag.get_text(strip=True)
                if text:
                    return text
        return None

    # ------------------------------------------------------------------
    # Construcción de DTOs desde dicts crudos
    # ------------------------------------------------------------------

    def _build_dto_fields(self, raw_data: dict, source: str) -> dict:
        """Construye los campos comunes para VehicleSearchResult/VehicleDetail."""
        return {
            "source": source,
            "external_id": raw_data.get("external_id", ""),
            "url": raw_data.get("url"),
            "brand": raw_data.get("brand"),
            "model": raw_data.get("model"),
            "category": raw_data.get("category"),
            "version": raw_data.get("version"),
            "year": raw_data.get("year"),
            "mileage": raw_data.get("mileage"),
            "fuel_type": raw_data.get("fuel_type"),
            "transmission": raw_data.get("transmission"),
            "power_hp": raw_data.get("power_hp"),
            "displacement_cc": raw_data.get("displacement_cc"),
            "doors": raw_data.get("doors"),
            "color": raw_data.get("color"),
            "emissions": raw_data.get("emissions"),
            "location": raw_data.get("location"),
            "seller_type": raw_data.get("seller_type"),
            "first_registration": raw_data.get("first_registration"),
            "price": raw_data.get("price"),
            "currency": raw_data.get("currency"),
            "vin": raw_data.get("vin"),
            "description": raw_data.get("description"),
            "images": raw_data.get("images", []),
            "equipment": raw_data.get("equipment", []),
            "raw_data": raw_data.get("raw_data", raw_data),
        }
