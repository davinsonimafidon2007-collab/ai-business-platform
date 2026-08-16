"""Etiquetas ES para recommendation y risk (REC.1)."""

from __future__ import annotations

RECOMMENDATION_LABELS_ES: dict[str, str] = {
    "BUY_NOW": "Comprar ya",
    "BUY": "Comprar",
    "WATCH": "Vigilar",
    "NEGOTIATE": "Negociar",
    "REJECT": "Descartar",
    "PASS": "Pasar",
    "CONSIDER": "Considerar",
    "WALK_AWAY": "Abandonar",
}

RISK_LABELS_ES: dict[str, str] = {
    "LOW": "Bajo",
    "MEDIUM": "Medio",
    "HIGH": "Alto",
    "CRITICAL": "Crítico",
    "NONE": "Ninguno",
    "UNKNOWN": "Desconocido",
}


def recommendation_label_es(code: str | None) -> str:
    if not code:
        return ""
    key = str(code).strip().upper()
    return RECOMMENDATION_LABELS_ES.get(key, key.replace("_", " ").title())


def risk_label_es(code: str | None) -> str:
    if not code:
        return ""
    key = str(code).strip().upper()
    return RISK_LABELS_ES.get(key, key.title())
