"""Parser puro de AutoScout24 (responsabilidad única).

Concentra las funciones de parseo de AutoScout24 que **no dependen** ni de
HTTP ni de ``self`` del provider:

- parseo del JSON embebido ``__NEXT_DATA__`` (vía más estable)
- mapeo de un objeto ``listing`` a ``VehicleSearchResult``
- helpers puros de precio / año / fuel / int parsing

``AutoScout24Provider`` delega aquí pero conserva su API pública estable
(``search``, ``get_vehicle``) y los métodos privados que usan sus tests.
Funciones predecibles y sin estado; el URL join necesita ``base_url``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

from app.providers.dto import VehicleSearchResult

logger = logging.getLogger(__name__)

# Precio de coche razonable en el dominio de importación (EUR)
_MIN_PLAUSIBLE_PRICE = 500.0
_MAX_PLAUSIBLE_PRICE = 500_000.0

_FUEL_PATTERNS = [
    (re.compile(r"benzin|petrol|gasolina", re.IGNORECASE), "Gasolina"),
    (re.compile(r"diesel", re.IGNORECASE), "Diesel"),
    (re.compile(r"elektro|electric", re.IGNORECASE), "Eléctrico"),
    (re.compile(r"hybrid", re.IGNORECASE), "Híbrido"),
    (re.compile(r"wasserstoff|hydrogen", re.IGNORECASE), "Hidrógeno"),
    (re.compile(r"lpg|cng|autogas", re.IGNORECASE), "Gas"),
]

# Mapa de códigos cortos de combustible (una sola letra) → etiqueta.
_FUEL_CODE_MAP = {
    "b": "Gasolina",
    "d": "Diesel",
    "e": "Eléctrico",
    "h": "Híbrido",
    "l": "Gas",
    "c": "Gas",
}


def parse_listings_from_next_data(
    html: str,
    base_url: str,
    source_name: str,
) -> list[VehicleSearchResult]:
    """Extrae listings desde el JSON embebido ``__NEXT_DATA__``.

    Args:
        html: Página de resultados de búsqueda de AutoScout24.
        base_url: URL base del provider (para resolver URLs relativas).
        source_name: Nombre del source (``autoscout24``).

    Returns:
        Lista de ``VehicleSearchResult`` extraídos (vacía si no hay JSON o
        no contiene ``listings``).
    """
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
        parsed = listing_dict_to_result(
            item,
            base_url=base_url,
            source_name=source_name,
        )
        if parsed is not None:
            results.append(parsed)
    return results


def listing_dict_to_result(
    item: dict[str, Any],
    base_url: str,
    source_name: str,
) -> VehicleSearchResult | None:
    """Mapea un objeto ``listing`` de pageProps a ``VehicleSearchResult``.

    Args:
        item: Objeto listing del JSON ``pageProps.listings``.
        base_url: URL base del provider (para resolver URLs relativas).
        source_name: Nombre del source (``autoscout24``).

    Returns:
        ``VehicleSearchResult`` normalizado, o ``None`` si el item no tiene
        un id externo válido.
    """
    external_id = str(
        item.get("id")
        or (item.get("identifier") or {}).get("crossReferenceId")
        or item.get("crossReferenceId")
        or ""
    ).strip()
    if not external_id:
        return None

    relative_url = item.get("url") or ""
    url = urljoin(f"{base_url}/", relative_url.lstrip("/")) if relative_url else None

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
        price = parse_price_text_static(str(price_obj.get("priceFormatted") or ""))

    mileage = parse_intish(
        tracking.get("mileage") or vehicle.get("mileageInKm")
    )
    year = year_from_registration(
        tracking.get("firstRegistration") or item.get("firstRegistration")
    )
    first_registration = tracking.get("firstRegistration")

    fuel_raw = vehicle.get("fuel") or tracking.get("fuelType")
    fuel_type = normalize_fuel(str(fuel_raw)) if fuel_raw else None

    transmission = vehicle.get("transmission")
    power_hp = parse_intish(vehicle.get("powerInHp") or vehicle.get("power"))
    displacement_cc = parse_intish(vehicle.get("engineDisplacementInCCM"))

    city = location_obj.get("city")
    zip_code = location_obj.get("zip")
    country = location_obj.get("countryCode")
    location_parts = [p for p in (zip_code, city, country) if p]
    location = " ".join(location_parts) if location_parts else None

    seller_type = seller.get("type")
    images = item.get("images") if isinstance(item.get("images"), list) else []
    images = [str(u) for u in images if u]

    return VehicleSearchResult(
        source=source_name,
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


def parse_intish(value: Any) -> int | None:
    """Convierte un valor arbitrario a entero, extrayendo solo dígitos.

    Args:
        value: Valor crudo (int, float, str con dígitos).

    Returns:
        Entero con los dígitos de ``value``, o ``None`` si no aplica.
    """
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


def year_from_registration(value: Any) -> int | None:
    """Extrae el año (20xx/19xx) de un valor de primera matriculación.

    Args:
        value: Valor crudo (p. ej. ``"03/2020"`` o ``"2020"``).

    Returns:
        Año como entero, o ``None`` si no se encuentra.
    """
    if value is None:
        return None
    text = str(value)
    match = re.search(r"(20\d{2}|19\d{2})", text)
    if match:
        return int(match.group(1))
    return None


def normalize_fuel(raw: str) -> str | None:
    """Normaliza el tipo de combustible a una etiqueta canónica.

    Acepta tanto códigos cortos (``b``, ``d``, ``e``, ``h``, ``l``, ``c``)
    como textos libres (``Benzin``, ``Diesel``...).

    Args:
        raw: Texto de combustible crudo.

    Returns:
        Etiqueta canónica, el texto original si no hay match, o ``None``.
    """
    text = (raw or "").strip()
    if not text:
        return None
    if len(text) == 1 and text.lower() in _FUEL_CODE_MAP:
        return _FUEL_CODE_MAP[text.lower()]
    for pattern, label in _FUEL_PATTERNS:
        if pattern.search(text):
            return label
    return text


def parse_price_text_static(text: str) -> float | None:
    """Parsea un texto de precio DE/EU a float.

    Acepta formatos ``28.500 €``, ``32.990 €``, ``12.345,- €``,
    ``12345 EUR``, ``9000.50``.

    Args:
        text: Texto que contiene el precio.

    Returns:
        Precio como float, o ``None`` si no se encuentra.
    """
    if not text:
        return None
    match = re.search(
        r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,}(?:,\d{1,2})?|\d{1,3},\d{2})\s*(?:€|EUR|eur)?",
        text,
    )
    if not match:
        # "9.000,-"
        match = re.search(r"(?<!\d)(\d{1,3}(?:\.\d{3})+)\s*,-", text)
    if not match:
        return None
    raw = match.group(1)
    if "," in raw and "." in raw:
        # 9.000,50 → european
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 2:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    else:
        # 9.000 miles or 9000.50 US — si hay más de un punto o patrón miles DE
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
            raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def coerce_price_number(value: Any) -> float | None:
    """Coerciona un valor de precio (número o texto simple) a float.

    Args:
        value: Valor crudo de precio.

    Returns:
        Precio como float, o ``None`` si no es convertible.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # "9000.00" or "9000"
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        try:
            return float(text)
        except ValueError:
            return None
    return parse_price_text_static(text)


def is_plausible_price(value: float) -> bool:
    """Indica si un precio está dentro del rango plausible de coches.

    Args:
        value: Precio en EUR.

    Returns:
        ``True`` si es plausible (500–500k EUR).
    """
    return _MIN_PLAUSIBLE_PRICE <= value <= _MAX_PLAUSIBLE_PRICE
