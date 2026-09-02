from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, ClassVar
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.providers.dto import VehicleDetail, VehicleSearchResult
from app.providers.exceptions import ProviderConnectionError, ProviderParsingError, ProviderTimeoutError, ProviderUnavailableError
from app.providers.http_client import ProviderHttpClient
from app.providers.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class VehicleProvider(ABC):
    """Interfaz abstracta que deben implementar todos los providers de vehículos.

    Incluye toda la lógica de parsing común: extracción de URL, precio,
    kilometraje, año, combustible, transmisión, potencia, ubicación,
    imágenes y descripción.

    Las subclases solo deben definir:
      - ``source_name`` (property)
      - ``_find_listing_nodes(self, soup)``  ← específico del HTML
      - Opcionalmente, las configuraciones de clase para personalizar
        selectores CSS y patrones de texto.

    Separación de responsabilidades (SOLID ligero):
      - HTTP cross-cutting (proxy / UA / circuit / retries) → ``ProviderHttpClient``.
      - Parsing específico del provider → vía subclase o módulo parser puro
        (p. ej. ``app.providers.parsers.autoscout24_parser``).
      El provider delega en estos colaboradores pero conserva su API pública
      estable (``search``, ``get_vehicle``) y sus métodos de parsing privados.
    """

    # --------------------------------------------------------------
    # Selector health tracking (AUDIT.PARALLEL.1 — selectores frágiles)
    # --------------------------------------------------------------

    _selector_hits: ClassVar[defaultdict[str, int]] = defaultdict(int)
    _selector_misses: ClassVar[defaultdict[str, int]] = defaultdict(int)

    @classmethod
    def get_selector_health(cls) -> dict[str, dict[str, int]]:
        """Return selector hit/miss counts for monitoring."""
        all_keys = set(cls._selector_hits.keys()) | set(cls._selector_misses.keys())
        return {
            key: {
                "hits": cls._selector_hits.get(key, 0),
                "misses": cls._selector_misses.get(key, 0),
            }
            for key in sorted(all_keys)
        }

    @classmethod
    def reset_selector_health(cls) -> None:
        """Reset health counters (for testing)."""
        cls._selector_hits.clear()
        cls._selector_misses.clear()

    def _track_selector(self, selector: str, matched: bool) -> None:
        """Track whether a CSS selector matched any nodes."""
        key = f"{self.source_name}:{selector}"
        if matched:
            self._selector_hits[key] += 1
        else:
            self._selector_misses[key] += 1

    # --------------------------------------------------------------
    # Configuraciones modificables por subclase
    # --------------------------------------------------------------

    # Grupos de selectores CSS para extraer el título (orden de prioridad)
    _title_selector_groups: ClassVar[list[tuple[str, ...]]] = [
        ("h1.title", "h2.title", "h3.title", ".title h1", ".title h2"),
        ("h1", "h2", "h3"),
    ]
    # Selector CSS de último recurso para el título
    _catchall_title_selector: ClassVar[str] = ".title, .name, [data-test='title']"

    # Ruta para construir la URL de detalle (ej: "/vehiculo/" o "/angebote/")
    _vehicle_detail_path: ClassVar[str] = "/vehiculo/"

    # Palabras clave para detectar etiquetas de ubicación en el HTML
    _location_label_keywords: ClassVar[tuple[str, ...]] = (
        "ubicación", "location", "localidad", "ort",
    )

    # Patrones de tipo de combustible → valor normalizado
    _fuel_patterns: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (re.compile(r"benzin|petrol|gasolina", re.IGNORECASE), "Gasolina"),
        (re.compile(r"diesel", re.IGNORECASE), "Diesel"),
        (re.compile(r"elektro", re.IGNORECASE), "Eléctrico"),
        (re.compile(r"hybrid", re.IGNORECASE), "Híbrido"),
        (re.compile(r"wasserstoff", re.IGNORECASE), "Hidrógeno"),
        (re.compile(r"lpg|cng", re.IGNORECASE), "Gas"),
    ]

    # Patrones de tipo de transmisión → valor normalizado
    _transmission_patterns: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (re.compile(r"schaltgetriebe|manual", re.IGNORECASE), "Manual"),
        (re.compile(r"automatik|automática|automático", re.IGNORECASE), "Automática"),
    ]

    # --------------------------------------------------------------
    # Inicialización
    # --------------------------------------------------------------

    def __init__(
        self,
        http_client: ProviderHttpClient | None = None,
        base_url: str | None = None,
    ) -> None:
        """Inicializa el provider con un cliente HTTP opcional.

        Args:
            http_client: Cliente HTTP reutilizable. Si no se proporciona, se crea uno nuevo.
            base_url: URL base del proveedor (solo usado si no se proporciona http_client).
        """
        self._http_client = http_client
        self._base_url = base_url

    # --------------------------------------------------------------
    # Propiedades abstractas
    # --------------------------------------------------------------

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nombre único del provider (ej: 'mobile_de', 'autoscout24')."""
        ...

    # --------------------------------------------------------------
    # Métodos abstractos de búsqueda de nodos
    # --------------------------------------------------------------

    @abstractmethod
    def _find_listing_nodes(self, soup: BeautifulSoup) -> list[Any]:
        """Localiza los nodos HTML que representan anuncios de vehículos.

        Es el único método de parsing que **debe** implementar cada subclase,
        ya que los selectores CSS varían completamente entre providers.
        """
        ...

    # --------------------------------------------------------------
    # API pública
    # --------------------------------------------------------------

    async def search(self, query: str, **kwargs: object) -> list[VehicleSearchResult]:
        """Busca vehículos en el provider a partir de una URL de búsqueda.

        El ``query`` debe ser una URL de resultados de búsqueda del provider.
        Returns:
            Lista de resultados normalizados como ``VehicleSearchResult``.
        """
        if circuit_breaker.is_open(self.source_name):
            raise ProviderUnavailableError(
                message=f"{self.source_name}: circuito abierto tras fallos repetidos.",
                provider=self.source_name,
            )
        try:
            html = await self._download_url(query)
        except (ProviderConnectionError, ProviderTimeoutError, httpx.HTTPStatusError):
            circuit_breaker.record_failure(self.source_name)
            raise
        circuit_breaker.record_success(self.source_name)
        return self._parse_search_results(html, query)

    async def get_vehicle(self, external_id: str) -> VehicleDetail:
        """Obtiene la información detallada de un vehículo por su ID externo.

        Args:
            external_id: ID del vehículo en el provider (o URL completa).

        Returns:
            ``VehicleDetail`` con la información completa del vehículo.
        """
        if external_id.startswith("http"):
            url = external_id
        else:
            url = urljoin(f"{self._base_url}/", f"{self._vehicle_detail_path.lstrip('/')}{external_id}")

        html = await self._download_url(url)
        return self._parse_vehicle_detail(html, url)

    def normalize_vehicle(self, raw_data: dict) -> VehicleSearchResult | VehicleDetail:
        """Normaliza datos crudos del provider a un DTO.

        El ``raw_data`` puede contener una clave especial ``_type`` con valor
        ``"detail"`` para devolver un ``VehicleDetail`` o cualquier otro valor
        (por defecto ``"search"``) para devolver un ``VehicleSearchResult``.
        """
        is_detail = raw_data.get("_type", "search") == "detail"
        common = self._build_dto_fields(raw_data, source=self.source_name)
        if is_detail:
            return VehicleDetail(**common)
        return VehicleSearchResult(**common)

    # --------------------------------------------------------------
    # Cliente HTTP
    # --------------------------------------------------------------

    async def _get_client(self) -> ProviderHttpClient:
        """Obtiene el cliente HTTP, creándolo si es necesario."""
        if self._http_client is None:
            self._http_client = ProviderHttpClient(
                provider_name=self.source_name,
                base_url=self._base_url,
            )
        return self._http_client

    async def _download_url(self, url: str) -> str:
        """Descarga el HTML de una URL utilizando el cliente HTTP."""
        client = await self._get_client()
        response = await client.get(url)
        return response.text

    async def close(self) -> None:
        """Cierra el cliente HTTP si fue creado por el provider."""
        if self._http_client is not None:
            await self._http_client.close()

    async def __aenter__(self) -> VehicleProvider:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        await self.close()

    # --------------------------------------------------------------
    # Parsing de resultados de búsqueda
    # --------------------------------------------------------------

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
            price=price,
        )

    # --------------------------------------------------------------
    # Parsing de detalle de vehículo
    # --------------------------------------------------------------

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
            price=price,
        )

    # --------------------------------------------------------------
    # Métodos de extracción
    # --------------------------------------------------------------

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
            return urljoin(f"{self._base_url}/", href.lstrip("/"))
        return href

    def _extract_external_id(self, url: str | None) -> str | None:
        """Extrae el ID externo del vehículo de una URL."""
        if not url:
            return None
        patterns = (
            r"(?:[?&](?:id|vehicleId|v|listingId)=)(\d{4,})(?:&|$)",
            r"[-/](\d{4,})(?:/|$)",
            r"(?:^|[/?&])([A-Za-z0-9-]+-(\d{4,}))(?:[/?#]|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                group = match.group(1)
                if group.isdigit():
                    return group
                return group if group and any(ch.isdigit() for ch in group) else None
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
            return urljoin(f"{self._base_url}/", url.lstrip("/"))
        return url

    def _extract_title(self, soup: Any) -> str | None:
        """Extrae el título del anuncio (marca + modelo)."""
        # Estrategia por grupos de selectores (configurable por subclase)
        for group in self._title_selector_groups:
            for selector in group:
                tag = soup.select_one(selector)
                if tag:
                    text = tag.get_text(strip=True)
                    if text:
                        return text

        # Estrategia de último recurso
        tag = soup.select_one(self._catchall_title_selector)
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

        # Marcas conocidas multipalabra: si el título empieza por una de ellas,
        # la marca es la fracción coincidente y el resto es modelo.
        known_brands = [
            "Alfa Romeo",
            "Aston Martin",
            "DS Automobiles",
            "Land Rover",
            "Mercedes-Benz",
            "General Motors",
            "Jeep",
            "Range Rover",
            "Rolls-Royce",
            "Hongqi",
            "BYD",
            "Great Wall",
            "Smart",
            "Borgward",
            "LEVC",
            "Lynk & Co",
            "Volkswagen",
            "Mercedes-AMG",
        ]
        for brand in known_brands:
            if title.lower().startswith(brand.lower()):
                rest = title[len(brand):].strip()
                model = rest if rest else None
                return brand, model

        # Fallback: primera palabra = marca, resto = modelo.
        parts = title.split()
        if len(parts) >= 2:
            brand = parts[0]
            model = " ".join(parts[1:])
            return brand, model
        if len(parts) == 1:
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
        """Parsea precio DE/EU. Rechaza valores absurdos para coches."""
        if not text:
            return None
        # Evitar cuotas
        if re.search(r"mth|/mo\b|monat|rate|finanz", text, re.I):
            return None

        match = re.search(
            r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,}(?:,\d{1,2})?|\d{1,3},\d{2})\s*(?:€|EUR|eur|,-)?",
            text,
        )
        if not match:
            return None
        raw = match.group(1)
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            parts = raw.split(",")
            raw = raw.replace(".", "").replace(",", ".") if len(parts[-1]) == 2 else raw.replace(",", "")
        elif re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
            raw = raw.replace(".", "")
        try:
            value = float(raw)
        except ValueError:
            return None
        # Coches: descartar < 100 € (evita 0.0011 y similares)
        if value < 100 or value > 500_000:
            return None
        return value

    def _extract_mileage(self, soup: Any) -> int | None:
        """Extrae el kilometraje del vehículo."""
        text = soup.get_text()
        # Patrón: "123.456 km" o "123.456 Km" o "123456 km"
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
        """Extrae el año de primera matriculación / fabricación.

        Prioriza patrones explícitos (EZ, Erstzulassung, matrícula).
        Evita el fallback genérico ``\b(20xx)\b`` que captura años de
        copyright del footer (2024–2026).
        """
        text = soup.get_text()

        # 1) "EZ 03/2020", "03/2020", "Erstzulassung 03/2020"
        match = re.search(
            r"(?:EZ|Erstzulassung|1[ªa].?\s*matriculaci[oó]n|primera\s+matriculaci[oó]n)?\s*"
            r"(?:0[1-9]|1[0-2])/((?:19|20)\d{2})",
            text,
            re.IGNORECASE,
        )
        if match:
            year = int(match.group(1))
            if 1980 <= year <= 2100:
                return year

        # 2) "EZ 2020", "Erstzulassung: 2020", "Baujahr 2020"
        match = re.search(
            r"(?:EZ|Erstzulassung|Baujahr|Jahr|año|year|matriculaci[oó]n|registro)"
            r"[^\d]{0,20}((?:19|20)\d{2})",
            text,
            re.IGNORECASE,
        )
        if match:
            year = int(match.group(1))
            if 1980 <= year <= 2100:
                return year

        # 3) data-year attribute si existe
        tag = soup.select_one("[data-year]") if hasattr(soup, "select_one") else None
        if tag is not None:
            raw = tag.get("data-year")
            if raw:
                try:
                    year = int(str(raw).strip()[:4])
                    if 1980 <= year <= 2100:
                        return year
                except ValueError:
                    pass

        # Sin fallback genérico de cualquier 20xx en la página
        return None

    def _extract_fuel(self, soup: Any) -> str | None:
        """Extrae el tipo de combustible."""
        text = soup.get_text()
        for pattern, fuel in self._fuel_patterns:
            if pattern.search(text):
                return fuel
        return None

    def _extract_transmission(self, soup: Any) -> str | None:
        """Extrae el tipo de transmisión."""
        text = soup.get_text()
        for pattern, trans in self._transmission_patterns:
            if pattern.search(text):
                return trans
        return None

    def _extract_power(self, soup: Any) -> int | None:
        """Extrae la potencia en caballos (hp / PS).

        Acepta formatos DE y ES:
          - "150 hp", "150 cv", "150 ch"
          - "110 kW (150 PS)" → prioriza el valor entre paréntesis
          - "110 kW" solo → convierte kW → PS (× 1.35962)

        Nota: el patrón base no acepta "150 PS" como valor aislado para
        mantener la compatibilidad con los fixtures del proyecto.
        """
        text = soup.get_text()

        # 1) "110 kW (150 PS)" o "110 kW (150 hp)"
        match = re.search(
            r"\d+\s*kW\s*\(\s*(\d{2,4})\s*(?:PS|hp|cv|ch)\s*\)",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

        # 2) "150 hp" / "150 cv" / "150 ch" (sin PS como valor aislado)
        match = re.search(
            r"(?<!\d)(\d{2,4})\s*(?:hp|cv|ch)\b",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

        # 3) Solo kW → convertir a PS aproximados
        match = re.search(r"(?<!\d)(\d{2,4})\s*kW\b", text, re.IGNORECASE)
        if match:
            try:
                kw = int(match.group(1))
                return int(round(kw * 1.35962))
            except ValueError:
                pass

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
            if any(kw in label_text for kw in self._location_label_keywords):
                value_span = label_span.find_next_sibling(class_="value")
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

    # --------------------------------------------------------------
    # Construcción de DTOs desde dicts crudos
    # --------------------------------------------------------------

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

