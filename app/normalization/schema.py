"""Normalized vehicle schema with comprehensive validation."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.providers.dto import VehicleDetail, VehicleSearchResult


class NormalizedEquipment(BaseModel):
    """Normalized equipment item with category."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = Field(None, max_length=100)
    original: str | None = Field(None, max_length=500)


class NormalizedVehicle(BaseModel):
    """Fully normalized vehicle entity with validation and traceability."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    # Core identifiers
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str = Field(..., min_length=1, max_length=50)
    external_id: str = Field(..., min_length=1, max_length=255)
    url: str | None = Field(None, max_length=2048)

    # Vehicle identification
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    version: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=50)

    # Temporal
    year: int | None = Field(None, ge=1900, le=2100)
    first_registration: str | None = Field(None, max_length=50)
    publication_date: datetime | None = None

    # Technical specs
    mileage: int | None = Field(None, ge=0, le=5_000_000)
    fuel_type: str | None = Field(None, max_length=50)
    transmission: str | None = Field(None, max_length=50)
    power_hp: int | None = Field(None, ge=1, le=2000)
    power_kw: int | None = Field(None, ge=1, le=1500)
    displacement_cc: int | None = Field(None, ge=50, le=10000)
    doors: int | None = Field(None, ge=1, le=8)
    color: str | None = Field(None, max_length=50)
    emissions: str | None = Field(None, max_length=50)

    # Location & seller
    location: str | None = Field(None, max_length=255)
    country: str | None = Field(None, max_length=2, pattern=r"^[A-Z]{2}$")
    seller_type: str | None = Field(None, max_length=50)

    # Pricing
    price: Decimal | None = Field(None, ge=0, le=10_000_000, decimal_places=2)
    currency: str = Field(default="EUR", max_length=3, pattern=r"^[A-Z]{3}$")
    price_eur: Decimal | None = Field(None, ge=0, le=10_000_000, decimal_places=2)

    # VIN & documentation
    vin: str | None = Field(None, max_length=17)

    # Media & description
    description: str | None = Field(None, max_length=50000)
    images: list[str] = Field(default_factory=list)
    equipment: list[NormalizedEquipment] = Field(default_factory=list)

    # Traceability & quality
    raw_data: dict[str, Any] = Field(default_factory=dict)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    quality_flags: list[str] = Field(default_factory=list)
    normalized_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("brand", "model", mode="before")
    @classmethod
    def clean_brand_model(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return clean_vehicle_string(v)

    @field_validator("version", mode="before")
    @classmethod
    def clean_version(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return clean_version_string(v)

    @field_validator("fuel_type", mode="before")
    @classmethod
    def normalize_fuel_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_fuel(v)

    @field_validator("transmission", mode="before")
    @classmethod
    def normalize_transmission(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_transmission(v)

    @field_validator("color", mode="before")
    @classmethod
    def normalize_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_color(v)

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) == 2 and v.isalpha():
            return v
        country_map = {
            "DE": "DE", "GERMANY": "DE", "ALEMANIA": "DE",
            "ES": "ES", "SPAIN": "ES", "ESPANA": "ES", "ESPAÑA": "ES",
            "FR": "FR", "FRANCE": "FR", "FRANCIA": "FR",
            "IT": "IT", "ITALY": "IT", "ITALIA": "IT",
            "PT": "PT", "PORTUGAL": "PT",
            "BE": "BE", "BELGIUM": "BE", "BELGICA": "BE",
            "NL": "NL", "NETHERLANDS": "NL", "HOLANDA": "NL",
            "AT": "AT", "AUSTRIA": "AT",
            "PL": "PL", "POLAND": "PL", "POLONIA": "PL",
        }
        return country_map.get(v.upper())

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: str | None) -> str:
        if v is None:
            return "EUR"
        v = v.strip().upper()
        currency_map = {
            "EUR": "EUR", "€": "EUR", "EURO": "EUR",
            "USD": "USD", "$": "USD", "DOLLAR": "USD",
            "GBP": "GBP", "£": "GBP", "POUND": "GBP",
            "CHF": "CHF",
        }
        return currency_map.get(v, v if len(v) == 3 else "EUR")

    @field_validator("price", mode="before")
    @classmethod
    def coerce_price(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if isinstance(v, (int, float)):
            return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if isinstance(v, str):
            parsed = parse_price_text(v)
            if parsed is not None:
                return Decimal(str(parsed)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return None

    @field_validator("mileage", mode="before")
    @classmethod
    def coerce_mileage(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            digits = re.sub(r"[^\d]", "", v)
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return None
        return None

    @field_validator("year", mode="before")
    @classmethod
    def coerce_year(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            match = re.search(r"(20\d{2}|19\d{2})", v)
            if match:
                return int(match.group(1))
            if v.isdigit() and len(v) == 4:
                return int(v)
        return None

    @field_validator("power_hp", mode="before")
    @classmethod
    def coerce_power_hp(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            digits = re.sub(r"[^\d]", "", v)
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return None
        return None

    @field_validator("power_kw", mode="before")
    @classmethod
    def coerce_power_kw(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            digits = re.sub(r"[^\d.]", "", v)
            if digits:
                try:
                    return int(float(digits))
                except ValueError:
                    return None
        return None

    @field_validator("displacement_cc", mode="before")
    @classmethod
    def coerce_displacement(cls, v: Any) -> int | None:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            digits = re.sub(r"[^\d]", "", v)
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return None
        return None

    @field_validator("images", mode="before")
    @classmethod
    def normalize_images(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            seen: set[str] = set()
            result: list[str] = []
            for img in v:
                if isinstance(img, str):
                    normalized = normalize_image_url(img)
                    if normalized and normalized not in seen:
                        seen.add(normalized)
                        result.append(normalized)
            return result
        return []

    @field_validator("equipment", mode="before")
    @classmethod
    def normalize_equipment(cls, v: Any) -> list[NormalizedEquipment]:
        if v is None:
            return []
        if isinstance(v, list):
            result: list[NormalizedEquipment] = []
            for item in v:
                if isinstance(item, str):
                    result.append(NormalizedEquipment(name=item.strip(), original=item.strip()))
                elif isinstance(item, dict):
                    result.append(NormalizedEquipment(**item))
            return result
        if isinstance(v, str):
            items = [x.strip() for x in v.split(",") if x.strip()]
            return [NormalizedEquipment(name=item, original=item) for item in items]
        return []

    @field_validator("vin", mode="before")
    @classmethod
    def normalize_vin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        # Remove any non-alphanumeric characters
        v = re.sub(r"[^A-Z0-9]", "", v)
        return v if v else None

    @model_validator(mode="after")
    def compute_price_eur(self) -> NormalizedVehicle:
        if self.price is not None and self.price_eur is None:
            object.__setattr__(self, "price_eur", convert_to_eur(self.price, self.currency))
        if self.power_hp is None and self.power_kw is not None:
            object.__setattr__(self, "power_hp", int(round(self.power_kw * 1.35962)))
        elif self.power_kw is None and self.power_hp is not None:
            object.__setattr__(self, "power_kw", int(round(self.power_hp / 1.35962)))
        return self

    @model_validator(mode="after")
    def validate_quality(self) -> NormalizedVehicle:
        object.__setattr__(self, "quality_score", compute_quality_score(self)[0])
        object.__setattr__(self, "quality_flags", compute_quality_score(self)[1])
        return self

    def to_sqlalchemy_dict(self) -> dict[str, Any]:
        """Convert to dict compatible with SQLAlchemy Vehicle model."""
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "url": self.url,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "version": self.version,
            "year": self.year,
            "mileage": self.mileage,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "power_hp": self.power_hp,
            "displacement_cc": self.displacement_cc,
            "doors": self.doors,
            "color": self.color,
            "emissions": self.emissions,
            "location": self.location,
            "seller_type": self.seller_type,
            "first_registration": self.first_registration,
            "price": float(self.price) if self.price else None,
            "currency": self.currency,
            "vin": self.vin,
            "description": self.description,
            "images": self.images if self.images else None,
            "equipment": ",".join(e.name for e in self.equipment) if self.equipment else None,
        }

    @classmethod
    def from_provider_dto(
        cls,
        dto: VehicleSearchResult | VehicleDetail,
        exchange_rates: dict[str, Decimal] | None = None,
    ) -> NormalizedVehicle:
        """Create NormalizedVehicle from provider DTO with full normalization."""
        raw_data = getattr(dto, "raw_data", {}) or {}
        if not raw_data and hasattr(dto, "__dict__"):
            raw_data = {k: v for k, v in dto.__dict__.items() if not k.startswith("_")}

        equipment_raw = getattr(dto, "equipment", []) or []

        # Extract year from first_registration if not directly provided
        year = dto.year
        if year is None and dto.first_registration:
            match = re.search(r"(20\d{2}|19\d{2})", dto.first_registration)
            if match:
                year = int(match.group(1))

        return cls(
            source=dto.source,
            external_id=dto.external_id,
            url=dto.url,
            brand=dto.brand or "",
            model=dto.model or "",
            version=dto.version,
            category=dto.category,
            year=year,
            mileage=dto.mileage,
            fuel_type=dto.fuel_type,
            transmission=dto.transmission,
            power_hp=dto.power_hp,
            displacement_cc=dto.displacement_cc,
            doors=getattr(dto, "doors", None),
            color=getattr(dto, "color", None),
            emissions=getattr(dto, "emissions", None),
            location=dto.location,
            country=extract_country_from_location(dto.location),
            seller_type=dto.seller_type,
            first_registration=dto.first_registration,
            price=dto.price,
            currency=dto.currency or "EUR",
            vin=dto.vin,
            description=dto.description,
            images=dto.images or [],
            equipment=equipment_raw,
            raw_data=raw_data,
            provider_metadata={
                "provider": dto.source,
                "fetched_at": datetime.now(UTC).isoformat(),
            },
        )


# Validation constants
MIN_PLAUSIBLE_PRICE_EUR = Decimal("500")
MAX_PLAUSIBLE_PRICE_EUR = Decimal("500000")
MAX_PLAUSIBLE_MILEAGE = 5_000_000
MIN_YEAR = 1900
MAX_YEAR = 2100


# Currency conversion (static rates, can be extended with live API)
EXCHANGE_RATES_TO_EUR: dict[str, Decimal] = {
    "EUR": Decimal("1.0"),
    "USD": Decimal("0.92"),
    "GBP": Decimal("1.17"),
    "CHF": Decimal("1.05"),
    "PLN": Decimal("0.23"),
    "CZK": Decimal("0.04"),
    "HUF": Decimal("0.0025"),
    "RON": Decimal("0.20"),
    "BGN": Decimal("0.51"),
    "HRK": Decimal("0.13"),
    "SEK": Decimal("0.087"),
    "NOK": Decimal("0.086"),
    "DKK": Decimal("0.13"),
}


def convert_to_eur(amount: Decimal, currency: str) -> Decimal:
    """Convert amount to EUR using static exchange rates."""
    rate = EXCHANGE_RATES_TO_EUR.get(currency.upper(), Decimal("1.0"))
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# String cleaning functions
_BRAND_ALIASES: dict[str, str] = {
    "vw": "Volkswagen",
    "v.w.": "Volkswagen",
    "volkswagen": "Volkswagen",
    "mercedes": "Mercedes-Benz",
    "mercedes benz": "Mercedes-Benz",
    "mb": "Mercedes-Benz",
    "bmw": "BMW",
    "b.m.w.": "BMW",
    "gm": "General Motors",
    "chev": "Chevrolet",
    "chevy": "Chevrolet",
    "land rover": "Land Rover",
    "range rover": "Land Rover",
    "alfa romeo": "Alfa Romeo",
    "alfa": "Alfa Romeo",
    "aston martin": "Aston Martin",
    "rolls royce": "Rolls-Royce",
    "rolls-royce": "Rolls-Royce",
}


def clean_vehicle_string(value: str) -> str:
    """Clean and normalize brand/model strings."""
    if not value:
        return value
    v = value.strip()
    v = re.sub(r"\s+", " ", v)
    v = v.strip(" .,-_")
    lower = v.lower()
    if lower in _BRAND_ALIASES:
        return _BRAND_ALIASES[lower]
    return v


def clean_version_string(value: str) -> str:
    """Clean version string: remove redundant brand/model prefixes."""
    if not value:
        return value
    v = value.strip()
    v = re.sub(r"\s+", " ", v)
    # Only remove leading digits if they look like a list prefix (e.g., "1. 320d" or "1) 320d")
    v = re.sub(r"^\d+[\.\)]\s+", "", v)
    return v.strip(" .,-_")


_FUEL_MAP: dict[str, str] = {
    "gasolina": "Gasolina",
    "petrol": "Gasolina",
    "benzin": "Gasolina",
    "b": "Gasolina",
    "diesel": "Diesel",
    "d": "Diesel",
    "electrico": "Eléctrico",
    "eléctrico": "Eléctrico",
    "electric": "Eléctrico",
    "elektro": "Eléctrico",
    "e": "Eléctrico",
    "hibrido": "Híbrido",
    "híbrido": "Híbrido",
    "hybrid": "Híbrido",
    "h": "Híbrido",
    "enchufable": "Híbrido Enchufable",
    "phev": "Híbrido Enchufable",
    "lpg": "GLP",
    "glp": "GLP",
    "cng": "GNC",
    "gnc": "GNC",
    "gas": "Gas",
    "autogas": "GLP",
    "hidrogeno": "Hidrógeno",
    "hidrógeno": "Hidrógeno",
    "hydrogen": "Hidrógeno",
    "wasserstoff": "Hidrógeno",
}


def normalize_fuel(value: str) -> str:
    """Normalize fuel type to canonical Spanish labels."""
    v = value.strip().lower()
    # Check for compound terms first (before removing spaces)
    if "enchufable" in v or "phev" in v:
        return "Híbrido Enchufable"
    if "hibrido" in v or "híbrido" in v or "hybrid" in v:
        return "Híbrido"
    v = re.sub(r"[^a-záéíóúüñ]", "", v)
    return _FUEL_MAP.get(v, value.strip().capitalize())


_TRANSMISSION_MAP: dict[str, str] = {
    "manual": "Manual",
    "schaltgetriebe": "Manual",
    "m": "Manual",
    "automatica": "Automática",
    "automática": "Automática",
    "automatic": "Automática",
    "automatik": "Automática",
    "a": "Automática",
    "dsg": "Automática (DSG)",
    "tronic": "Automática",
    "tiptronic": "Automática (Tiptronic)",
    "multitronic": "Automática (Multitronic)",
    "cvt": "Automática (CVT)",
    "semi-automatica": "Semiautomática",
    "semiautomatica": "Semiautomática",
    "semi-automatic": "Semiautomática",
    "robotizada": "Automatizada",
    "automatizada": "Automatizada",
}


def normalize_transmission(value: str) -> str:
    """Normalize transmission to canonical Spanish labels."""
    v = value.strip().lower()
    # Check for specific patterns before removing special chars
    if "dsg" in v:
        return "Automática (DSG)"
    if "tiptronic" in v:
        return "Automática (Tiptronic)"
    if "multitronic" in v:
        return "Automática (Multitronic)"
    if "cvt" in v:
        return "Automática (CVT)"
    v = re.sub(r"[^a-záéíóúüñ]", "", v)
    return _TRANSMISSION_MAP.get(v, value.strip().capitalize())


_COLOR_MAP: dict[str, str] = {
    "negro": "Negro",
    "black": "Negro",
    "blanco": "Blanco",
    "white": "Blanco",
    "gris": "Gris",
    "gray": "Gris",
    "grey": "Gris",
    "plata": "Plata",
    "silver": "Plata",
    "azul": "Azul",
    "blue": "Azul",
    "rojo": "Rojo",
    "red": "Rojo",
    "verde": "Verde",
    "green": "Verde",
    "amarillo": "Amarillo",
    "yellow": "Amarillo",
    "naranja": "Naranja",
    "orange": "Naranja",
    "marron": "Marrón",
    "marrón": "Marrón",
    "brown": "Marrón",
    "beige": "Beige",
    "dorad": "Dorado",
    "gold": "Dorado",
    "violet": "Violeta",
    "violeta": "Violeta",
}


def normalize_color(value: str) -> str:
    """Normalize color to canonical Spanish labels."""
    v = value.strip().lower()
    v = re.sub(r"[^a-záéíóúüñ]", "", v)
    for key, label in _COLOR_MAP.items():
        if key in v:
            return label
    return value.strip().capitalize()


def extract_country_from_location(location: str | None) -> str | None:
    """Extract ISO country code from location string."""
    if not location:
        return None
    location_lower = location.lower()
    country_patterns = {
        "DE": ["deutschland", "germany", "de ", " de", ", de", "berlin", "munich", "hamburg", "köln", "frankfurt"],
        "ES": ["españa", "espana", "spain", " es", ", es", "madrid", "barcelona", "valencia", "sevilla", "bilbao"],
        "FR": ["france", "france", " fr", ", fr", "paris", "lyon", "marseille"],
        "IT": ["italia", "italy", " it", ", it", "roma", "milano", "napoli"],
        "PT": ["portugal", " pt", ", pt", "lisboa", "porto"],
        "BE": ["belgique", "belgie", "belgium", " be", ", be", "brussels", "bruxelles"],
        "NL": ["nederland", "holland", " netherlands", " nl", ", nl", "amsterdam", "rotterdam"],
        "AT": ["osterreich", "österreich", "austria", " at", ", at", "wien", "vienna"],
        "PL": ["polska", "poland", " pl", ", pl", "warszawa", "krakow"],
    }
    for code, patterns in country_patterns.items():
        for pattern in patterns:
            if pattern in location_lower:
                return code
    return None


def parse_price_text(text: str) -> float | None:
    """Parse price text in various European formats."""
    if not text:
        return None
    text = text.strip()
    if re.search(r"mth|/mo\b|monat|rate|finanz|cuota|mensual", text, re.I):
        return None
    match = re.search(
        r"(?<!\d)(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d{4,}(?:[.,]\d{1,2})?|\d{1,3}[.,]\d{2})\s*(?:€|EUR|eur|\$|USD|£|GBP|CHF)?",
        text,
    )
    if not match:
        match = re.search(r"(?<!\d)(\d{1,3}(?:[.,]\d{3})+)\s*,-", text)
    if not match:
        return None
    raw = match.group(1)
    if "," in raw and "." in raw:
        last_comma = raw.rfind(",")
        last_dot = raw.rfind(".")
        if last_comma > last_dot:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 2:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def normalize_image_url(url: str) -> str:
    """Normalize image URL."""
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return url
    return url


def validate_vin(vin: str | None) -> bool:
    """Validate VIN format (basic 17-char alphanumeric, no I/O/Q)."""
    if not vin:
        return False
    vin = vin.strip().upper()
    if len(vin) != 17:
        return False
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        return False
    return True


def compute_quality_score(vehicle: NormalizedVehicle) -> tuple[float, list[str]]:
    """Compute quality score and flags for a normalized vehicle."""
    score = 1.0
    flags: list[str] = []

    required_fields = ["brand", "model", "year", "price", "mileage"]
    for field in required_fields:
        if getattr(vehicle, field) is None:
            score -= 0.15
            flags.append(f"missing_{field}")

    if vehicle.price is not None:
        price_eur = vehicle.price_eur or convert_to_eur(vehicle.price, vehicle.currency)
        if price_eur < MIN_PLAUSIBLE_PRICE_EUR or price_eur > MAX_PLAUSIBLE_PRICE_EUR:
            score -= 0.2
            flags.append("price_out_of_range")

    if vehicle.mileage is not None:
        if vehicle.mileage < 0 or vehicle.mileage > MAX_PLAUSIBLE_MILEAGE:
            score -= 0.2
            flags.append("mileage_out_of_range")
        elif vehicle.year is not None:
            age = datetime.now().year - vehicle.year
            expected_max = age * 50000 + 50000
            if vehicle.mileage > expected_max:
                score -= 0.1
                flags.append("high_mileage_for_age")

    if vehicle.year is not None:
        current_year = datetime.now().year
        if vehicle.year < MIN_YEAR or vehicle.year > current_year + 1:
            score -= 0.15
            flags.append("year_out_of_range")

    if vehicle.vin and not validate_vin(vehicle.vin):
        score -= 0.1
        flags.append("invalid_vin_format")

    if not vehicle.images:
        score -= 0.05
        flags.append("no_images")

    if not vehicle.equipment:
        score -= 0.05
        flags.append("no_equipment")

    if not vehicle.description or (vehicle.description and len(vehicle.description) < 50):
        score -= 0.05
        flags.append("short_description")

    score = max(0.0, min(1.0, score))
    return score, flags


def detect_corrupt_listing(vehicle: NormalizedVehicle) -> list[str]:
    """Detect potentially corrupt/scam listings."""
    flags: list[str] = []

    if vehicle.price is not None:
        price_eur = vehicle.price_eur or convert_to_eur(vehicle.price, vehicle.currency)
        if price_eur < Decimal("1000"):
            flags.append("price_too_low")
        if vehicle.year and vehicle.year >= 2020 and price_eur < Decimal("5000"):
            flags.append("recent_car_price_too_low")

    if vehicle.mileage is not None and vehicle.year is not None:
        age = datetime.now().year - vehicle.year
        if age > 0 and vehicle.mileage < age * 1000:
            flags.append("mileage_suspiciously_low")

    if vehicle.power_hp is not None and vehicle.displacement_cc is not None:
        hp_per_liter = vehicle.power_hp / (vehicle.displacement_cc / 1000)
        if hp_per_liter > 300:
            flags.append("power_to_displacement_ratio_extreme")

    if vehicle.brand and vehicle.model:
        brand_lower = vehicle.brand.lower()
        model_lower = vehicle.model.lower()
        if brand_lower in model_lower:
            pass
        elif any(x in model_lower for x in ["bmw", "audi", "mercedes", "vw", "volkswagen"]):
            if brand_lower not in ["bmw", "audi", "mercedes-benz", "volkswagen"]:
                flags.append("brand_model_mismatch")

    if vehicle.images:
        for img in vehicle.images:
            if "placeholder" in img.lower() or "default" in img.lower():
                flags.append("placeholder_images")
                break

    return flags


def deduplicate_vehicles(
    vehicles: list[NormalizedVehicle],
    prefer_source_order: list[str] | None = None,
) -> list[NormalizedVehicle]:
    """Deduplicate vehicles by VIN, then by (source, external_id), then by (brand, model, year, mileage)."""
    if not vehicles:
        return []

    prefer_order = prefer_source_order or [
        "coches_net",
        "autoscout24_es",
        "autoscout24",
        "mobile_de",
        "es_market_fixture",
    ]

    # Group by VIN first
    by_vin: dict[str, list[NormalizedVehicle]] = {}
    no_vin: list[NormalizedVehicle] = []

    for v in vehicles:
        if v.vin and validate_vin(v.vin):
            by_vin.setdefault(v.vin.upper(), []).append(v)
        else:
            no_vin.append(v)

    result: list[NormalizedVehicle] = []

    # Deduplicate by VIN
    for vin_group in by_vin.values():
        if len(vin_group) == 1:
            result.append(vin_group[0])
        else:
            preferred = select_preferred_vehicle(vin_group, prefer_order)
            preferred.quality_flags.append("deduped_by_vin")
            result.append(preferred)

    # Deduplicate remaining by (source, external_id)
    by_source_ext: dict[tuple[str, str], list[NormalizedVehicle]] = {}
    for v in no_vin:
        key = (v.source, v.external_id)
        by_source_ext.setdefault(key, []).append(v)

    for group in by_source_ext.values():
        if len(group) == 1:
            result.append(group[0])
        else:
            preferred = select_preferred_vehicle(group, prefer_order)
            preferred.quality_flags.append("deduped_by_source_ext")
            result.append(preferred)

    # Deduplicate by fuzzy match (brand, model, year, mileage ±5%)
    fuzzy_groups: dict[str, list[NormalizedVehicle]] = {}
    for v in result:
        if v.brand and v.model and v.year and v.mileage:
            # Use 5% mileage buckets for fuzzy matching
            mileage_bucket = int(v.mileage / 5000) * 5000
            key = f"{v.brand.lower()}|{v.model.lower()}|{v.year}|{mileage_bucket}"
            fuzzy_groups.setdefault(key, []).append(v)

    final: list[NormalizedVehicle] = []
    processed: set[int] = set()

    for group in fuzzy_groups.values():
        if len(group) == 1:
            final.append(group[0])
        else:
            preferred = select_preferred_vehicle(group, prefer_order)
            preferred.quality_flags.append("deduped_fuzzy")
            final.append(preferred)
        for v in group:
            processed.add(id(v))

    for v in result:
        if id(v) not in processed:
            final.append(v)

    return final


def select_preferred_vehicle(
    vehicles: list[NormalizedVehicle],
    prefer_order: list[str],
) -> NormalizedVehicle:
    """Select the best vehicle from a duplicate group.

    Priority order:
    1. Quality score (higher is better) - primary
    2. Source preference (lower index in prefer_order is better) - secondary
    3. Richness (images + equipment count) - tertiary
    """
    def priority(v: NormalizedVehicle) -> tuple[float, int, int]:
        source_prio = prefer_order.index(v.source) if v.source in prefer_order else 999
        # Negative quality for min() - lower tuple = better
        # Use quality * 1000 to make it dominate over source_prio (0-999)
        return (-v.quality_score * 1000, source_prio, -(len(v.images) + len(v.equipment)))

    return min(vehicles, key=priority)


# Backwards compatibility exports
__all__ = [
    "NormalizedVehicle",
    "NormalizedEquipment",
    "convert_to_eur",
    "clean_vehicle_string",
    "clean_version_string",
    "normalize_fuel",
    "normalize_transmission",
    "normalize_color",
    "extract_country_from_location",
    "parse_price_text",
    "normalize_image_url",
    "validate_vin",
    "compute_quality_score",
    "detect_corrupt_listing",
    "deduplicate_vehicles",
    "select_preferred_vehicle",
    "EXCHANGE_RATES_TO_EUR",
    "MIN_PLAUSIBLE_PRICE_EUR",
    "MAX_PLAUSIBLE_PRICE_EUR",
    "MAX_PLAUSIBLE_MILEAGE",
    "MIN_YEAR",
    "MAX_YEAR",
]