"""Tests fiscales del IEDMT (BAJO.008/GRAVE.008).

El IEDMT es un % de la base imponible según el tramo de CO₂, no un importe
fijo. Estos tests fijan los valores de la normativa 2025 para detectar
regresiones si alguien toca las tablas.
"""

from __future__ import annotations

import pytest

from app.services.iedmt import (
    IEDMT_BRACKETS,
    IEDMT_VERSION,
    iedmt_plus_vat,
    iedmt_rate,
    iedmt_tax,
    parse_co2_gkm,
)

# (co2_gkm, rate_esperada) — normativa 2025
RATE_CASES = [
    (0.0, 0.0),
    (120.0, 0.0),
    (120.01, 0.0475),
    (140.0, 0.0475),
    (159.0, 0.0475),
    (159.01, 0.0975),
    (180.0, 0.0975),
    (199.0, 0.0975),
    (199.01, 0.1475),
    (300.0, 0.1475),
]


@pytest.mark.parametrize(("co2", "rate"), RATE_CASES)
def test_iedmt_rate_by_co2(co2: float, rate: float) -> None:
    assert iedmt_rate(co2) == rate


def test_iedmt_rate_none_or_negative_is_zero() -> None:
    assert iedmt_rate(None) == 0.0
    assert iedmt_rate(-5.0) == 0.0


def test_iedmt_tax_is_percentage_of_base() -> None:
    # 140 g/km → 4.75% de la base, no un importe fijo
    assert iedmt_tax(140.0, 10000.0) == pytest.approx(475.0)
    assert iedmt_tax(140.0, 50000.0) == pytest.approx(2375.0)
    # 180 g/km → 9.75%
    assert iedmt_tax(180.0, 10000.0) == pytest.approx(975.0)
    # >=200 → 14.75%
    assert iedmt_tax(210.0, 10000.0) == pytest.approx(1475.0)
    # exento
    assert iedmt_tax(100.0, 10000.0) == 0.0


def test_iedmt_tax_zero_base_or_unknown_co2() -> None:
    assert iedmt_tax(140.0, 0.0) == 0.0
    assert iedmt_tax(None, 10000.0) == 0.0
    assert iedmt_tax(0.0, 10000.0) == 0.0


def test_iedmt_plus_vat() -> None:
    result = iedmt_plus_vat(140.0, 10000.0)
    assert result["iedmt"] == pytest.approx(475.0)
    assert result["vat"] == pytest.approx(2100.0)
    assert result["total_taxes"] == pytest.approx(2575.0)


def test_parse_co2_gkm() -> None:
    assert parse_co2_gkm("120 g/km") == 120.0
    assert parse_co2_gkm("CO2: 145") == 145.0
    assert parse_co2_gkm("95g CO2") == 95.0
    assert parse_co2_gkm("112") is None
    assert parse_co2_gkm(None) is None


def test_version_and_brackets_sanity() -> None:
    assert IEDMT_VERSION == "2025"
    assert len(IEDMT_BRACKETS) == 4
    # Los tramos deben cubrir todo el rango y los tipos deben ser fracciones.
    rates = [b.tax_rate for b in IEDMT_BRACKETS]
    assert all(0.0 <= r <= 1.0 for r in rates)
    assert [0.0, 0.0475, 0.0975, 0.1475] == rates
