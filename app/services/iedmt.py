"""CO₂ emission parser and IEDMT tax calculator.

The IEDMT (Impuesto Especial sobre los Vehículos de Tracción Mecánica) is a
Spanish tax on first registration based on vehicle CO₂ emissions in g/km.
This module provides:

1. ``parse_co2_gkm`` — extracts numeric g/km from free-text provider data.
2. ``iedmt_rate`` — returns the tax rate (0..1) for a given CO₂ value.
3. ``iedmt_tax`` — calculates the IEDMT amount as ``rate * taxable base``.
4. ``iedmt_plus_vat`` — combines IEDMT + standard VAT for full tax picture.

GRAVE.008: el IEDMT real es un porcentaje de la base imponible según el tramo
de CO₂, no un importe fijo por vehículo. Los tramos reflejan la normativa 2025
(BOE/RD-ley 14/2022): 0% hasta 120 g/km, 4.75% de 121 a 159, 9.75% de 160 a
199, 14.75% desde 200. Se actualizan anualmente; la versión se rastrea en
``IEDMT_VERSION``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

IEDMT_VERSION = "2025"

# ---------------------------------------------------------------------------
# CO₂ parser
# ---------------------------------------------------------------------------

# Common patterns in provider data:
#   "120 g/km", "CO2: 145", "145g CO₂", "112", "95 gCO2/km"
_CO2_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\d+(?:[.,]\d+)?)\s*g\s*/?\s*k?m", re.IGNORECASE),
    re.compile(r"co2?\s*[:=]\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE),
    re.compile(r"(\d+(?:[.,]\d+)?)\s*g\s*co2", re.IGNORECASE),
]


def parse_co2_gkm(emissions_str: str | None) -> float | None:
    """Extract CO₂ emissions in g/km from a free-text string.

    Returns ``None`` if no numeric value can be extracted.
    """
    if not emissions_str:
        return None
    for pattern in _CO2_PATTERNS:
        m = pattern.search(emissions_str)
        if m:
            raw = m.group(1).replace(",", ".")
            try:
                value = float(raw)
                if 0 < value < 1000:  # sanity check
                    return value
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# IEDMT brackets (Spain, passenger vehicles, 2025)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IedmtBracket:
    co2_min: float  # g/km inclusive
    co2_max: float | None  # g/km inclusive (None = no upper limit)
    tax_rate: float  # fraction of the taxable base (0..1)


# Source: BOE-RD-ley 14/2022 (types for M1/terrestres). Rates as fraction.
IEDMT_BRACKETS: tuple[IedmtBracket, ...] = (
    IedmtBracket(0, 120, 0.0),
    IedmtBracket(120.01, 159, 0.0475),
    IedmtBracket(159.01, 199, 0.0975),
    IedmtBracket(199.01, None, 0.1475),
)


def iedmt_rate(co2_gkm: float | None) -> float:
    """Return the IEDMT tax rate (0..1) for a given CO₂ value in g/km.

    Args:
        co2_gkm: CO₂ emissions in g/km. If None or <=0, returns 0.0.

    Returns:
        Tax rate as a fraction (0.0, 0.0475, 0.0975 or 0.1475).
    """
    if co2_gkm is None or co2_gkm <= 0:
        return 0.0
    for bracket in IEDMT_BRACKETS:
        if co2_gkm <= (bracket.co2_max or float("inf")):
            return bracket.tax_rate
    return IEDMT_BRACKETS[-1].tax_rate


def iedmt_tax(co2_gkm: float | None, tax_base: float) -> float:
    """Calculate IEDMT tax amount in EUR as ``rate * taxable base``.

    Args:
        co2_gkm: CO₂ emissions in g/km. If None or <=0, returns 0.
        tax_base: Base imponible (valor del vehículo) en EUR.

    Returns:
        IEDMT tax amount in EUR (0.0 if emissions unknown).
    """
    if co2_gkm is None or co2_gkm <= 0 or tax_base <= 0:
        return 0.0
    return round(tax_base * iedmt_rate(co2_gkm), 2)


# ---------------------------------------------------------------------------
# Combined tax helper
# ---------------------------------------------------------------------------

VAT_RATE_SPAIN = 0.21  # 21% IVA general


def iedmt_plus_vat(
    co2_gkm: float | None,
    purchase_price: float,
    vat_rate: float = VAT_RATE_SPAIN,
) -> dict[str, float]:
    """Calculate IEDMT + VAT for a vehicle.

    Returns dict with keys: ``iedmt``, ``vat``, ``total_taxes``.
    The flat ``tax_rate`` from the profile (IVA on purchase price) is
    replaced by this more accurate calculation when CO₂ data is available.
    """
    iedmt = iedmt_tax(co2_gkm, purchase_price)
    vat = purchase_price * vat_rate
    return {
        "iedmt": round(iedmt, 2),
        "vat": round(vat, 2),
        "total_taxes": round(iedmt + vat, 2),
    }
