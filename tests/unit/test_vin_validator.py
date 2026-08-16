"""Tests del validador VIN ISO 3779 (TASK-017).

Cubre: estructura de 17 caracteres, juego de caracteres (sin I/O/Q),
check digit (posición 9) usando ejemplos documentados como válidos, y la
normalización a mayúsculas.
"""

from __future__ import annotations

import pytest

from app.utils.vin_validator import (
    compute_check_digit,
    transliterate_char,
    validate_vin,
)

# Ejemplos documentados con check digit correcto (NHTSA/SAE J853).
VALID_WITH_CHECK = {
    # Ejemplo clásico: check digit "X"
    "1M8GDM9AXKP042788": "X",
    # Honda (documentado en varios recursos como válido)
    "1HGCM82633A004352": "3",
}


class TestStructure:
    def test_accepts_valid_vin(self) -> None:
        for vin in VALID_WITH_CHECK:
            ok, reason = validate_vin(vin)
            assert ok is True, (vin, reason)

    @pytest.mark.parametrize(
        "vin",
        [
            "",  # vacío
            "1M8GDM9AXKP04278",  # 16 caracteres
            "1M8GDM9AXKP0427888",  # 18 caracteres
            "1M8GDM9AXKP04278I",  # I no permitido
            "1M8GDM9AXKP04278O",  # O no permitido
            "1M8GDM9AXKP04278Q",  # Q no permitido
            "1234567890123456_",  # carácter inválido
            "1M8GDM9A K P042788",  # espacios
        ],
    )
    def test_rejects_invalid_vin(self, vin: str) -> None:
        ok, reason = validate_vin(vin)
        assert ok is False, (vin, reason)
        assert reason

    def test_normalizes_to_uppercase(self) -> None:
        ok, _ = validate_vin("1m8gdm9axkp042788")
        assert ok is True


class TestCheckDigit:
    @pytest.mark.parametrize(
        ("vin", "expected"),
        list(VALID_WITH_CHECK.items()),
    )
    def test_compute_matches_expected(self, vin: str, expected: str) -> None:
        assert compute_check_digit(vin) == expected

    def test_check_digit_passes_for_valid_examples(self) -> None:
        for vin in VALID_WITH_CHECK:
            ok, reason = validate_vin(vin, check_digit=True)
            assert ok is True, (vin, reason)

    def test_check_digit_rejects_modified_vin(self) -> None:
        # Mutamos un carácter (fuera de la posición 9) → el check no coincide.
        bad = list("1M8GDM9AXKP042788")
        bad[1] = "2"
        ok, reason = validate_vin("".join(bad), check_digit=True)
        assert ok is False
        assert "control" in reason

    def test_compute_returns_none_for_invalid_shape(self) -> None:
        assert compute_check_digit("short") is None
        assert compute_check_digit("12345678901234567I") is None


class TestTransliteration:
    @pytest.mark.parametrize(
        ("char", "expected"),
        [
            ("0", 0),
            ("9", 9),
            ("A", 1),
            ("B", 2),
            ("C", 3),
            ("D", 4),
            ("E", 5),
            ("F", 6),
            ("G", 7),
            ("H", 8),
            ("J", 1),
            ("K", 2),
            ("L", 3),
            ("M", 4),
            ("N", 5),
            ("P", 7),
            ("R", 9),
            ("S", 2),
            ("T", 3),
            ("U", 4),
            ("V", 5),
            ("W", 6),
            ("X", 7),
            ("Y", 8),
            ("Z", 9),
        ],
    )
    def test_transliteration_table(self, char: str, expected: int) -> None:
        assert transliterate_char(char) == expected