"""VIN (Vehicle Identification Number) validation — ISO 3779 / NHTSA.

TASK-017 (FASE 9):

- Estructura ISO 3779: 17 caracteres alfanuméricos (excluye I, O, Q).
- Dígito de control (posición 9) según el estándar NHTSA/SAE J853:
  transliteración + pesos [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2] módulo 11.
- El dígito de control es **opcional**: muchos anuncios/proveedores no lo
  incluyen o usan marcadores sin validar. Por eso ``validate_vin`` valida la
  forma (17 chars + Juego de caracteres válido) y solo comprueba el check
  digit cuando el cliente lo pide explícitamente (``check_digit=True``).
"""

from __future__ import annotations

import re

# Caracteres permitidos: 0-9 y A-Z salvo I, O, Q.
_INVALID_CHARS = re.compile(r"[IOQ]")
_VIN_RE = re.compile(r"^[0-9A-HJ-NPR-Z]{17}$")

# Transliteración de letras a valores numéricos (position 9 check).
_TRANSLIT = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}
# Pesos por posición (1-indexada por ISO 3779: pos 1..17).
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def transliterate_char(char: str) -> int:
    """Devuelve el valor numérico de un carácter VIN (dígito = sí mismo)."""
    value = _TRANSLIT.get(char)
    if value is not None:
        return value
    return int(char)


def compute_check_digit(vin: str) -> str | None:
    """Calcula el dígito de control (posición 9) de un VIN de 17 caracteres.

    Devuelve el carácter ``'0'..'9'`` o ``'X'``; o ``None`` si ``vin`` no tiene
    la forma ISO 3779 válida (17 chars / juego de caracteres).
    """
    cleaned = (vin or "").strip().upper()
    if not _VIN_RE.match(cleaned):
        return None

    total = 0
    for i in range(17):
        if i == 8:
            continue  # la posición 9 es el propio check digit
        total += transliterate_char(cleaned[i]) * _WEIGHTS[i]

    remainder = total % 11
    # El check digit es el resto: 10 se representa como "X".
    if remainder == 10:
        return "X"
    return str(remainder)


def validate_vin(
    vin: str,
    check_digit: bool = False,
) -> tuple[bool, str]:
    """Valida un VIN ISO 3779.

    Args:
        vin: cadena a validar (17 caracteres).
        check_digit: si ``True`` también verifica el dígito de control de la
            posición 9 (init. por ``False`` porque muchos orígenes no lo traen).

    Returns:
        ``(ok, reason)``. Si es válido, reason = ``"ok"``.
    """
    cleaned = (vin or "").strip().upper()
    if not cleaned:
        return False, "VIN vacío"
    if len(cleaned) != 17:
        return False, f"El VIN debe tener 17 caracteres (tiene {len(cleaned)})"
    if _INVALID_CHARS.search(cleaned):
        return False, "El VIN contiene caracteres no válidos (I, O o Q)"
    if not _VIN_RE.match(cleaned):
        return False, "El VIN contiene caracteres no alfanuméricos permitidos"

    if check_digit:
        expected = compute_check_digit(cleaned)
        actual = cleaned[8]
        if expected is None or expected != actual:
            return False, "El dígito de control (posición 9) no coincide"

    return True, "ok"