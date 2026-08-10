"""CO₂ emission parser and IEDMT tax calculator.

The IEDMT (Impuesto Especial sobre los Vehículos de Tracción Mechánica)
is a Spanish tax based on vehicle CO₂ emissions in g/km. This module
provides:

1. ``parse_co2_gkm`` — extracts numeric g/km from free-text provider data.
2. ``iedmt_tax`` — calculates the IEDMT amount using DGT bracketed tables.
3. ``iedmt_plus_vat`` — combines IEDMT + standard VAT for full tax picture.

The brackets below reflect the 2025 DGT resolution for passenger vehicles.
They are updated annually; the version is tracked in ``IEDMT_VERSION``.
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
    tax_eur: float  # flat EUR amount per vehicle


# Source: BOE-RD-ley 20/2022 + updates. Values in EUR.
IEDMT_BRACKETS: tuple[IedmtBracket, ...] = (
    IedmtBracket(0, 120, 0.0),
    IedmtBracket(120.01, 140, 50.0),
    IedmtBracket(140.01, 160, 100.0),
    IedmtBracket(160.01, 180, 150.0),
    IedmtBracket(180.01, 200, 200.0),
    IedmtBracket(200.01, 250, 300.0),
    IedmtBracket(250.01, None, 400.0),
)


def iedmt_tax(co2_gkm: float | None) -> float:
    """Calculate IEDMT tax amount in EUR based on CO₂ emissions.

    Args:
        co2_gkm: CO₂ emissions in g/km. If None or <=0, returns 0.

    Returns:
        IEDMT tax amount in EUR (0.0 if emissions unknown).
    """
    if co2_gkm is None or co2_gkm <= 0:
        return 0.0
    for bracket in IEDMT_BRACKETS:
        if co2_gkm <= (bracket.co2_max or float("inf")):
            return bracket.tax_eur
    return IEDMT_BRACKETS[-1].tax_eur


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
    iedmt = iedmt_tax(co2_gkm)
    vat = purchase_price * vat_rate
    return {
        "iedmt": round(iedmt, 2),
        "vat": round(vat, 2),
        "total_taxes": round(iedmt + vat, 2),
    }
