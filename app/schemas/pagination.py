"""Cursor pagination schemas (TASK-019).

Paginación keyset (cursor) para listados grandes: en vez de OFFSET, cada página
devuelve un ``next_cursor`` opaco (base64) que codifica el punto exacto donde
empezar la siguiente (created_at DESC, id DESC). Estable y O(1) frente a
``skip`` profundo (PERF-001 / MAX_LIST_DEPTH).
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

from pydantic import BaseModel


class CursorPage[T](BaseModel):
    """Página paginada con cursor: ``items`` + token para la siguiente página.

    - ``next_cursor``: token base64 a pasar como ``?cursor=...``. ``None``
      cuando no hay más páginas.
    - ``has_more``: conveniencia para el frontend (== ``next_cursor`` no vacío).
    - ``total``: nº total de filas que cumplen el filtro (COUNT de la misma
      query).
    """

    items: list[T]
    total: int
    has_more: bool
    next_cursor: str | None = None
    limit: int = 20


def encode_cursor(created_at: datetime, resource_id: str) -> str:
    """Codifica el punto de paginación a un token base64 opaco.

    El cursor ordena por ``created_at DESC, id DESC`` (tie-break estable por id,
    ya que ``created_at`` puede repetirse). La hora se normaliza a UTC ISO.
    """
    normalized = created_at if created_at.tzinfo is not None else created_at.replace(
        tzinfo=UTC
    )
    payload = json.dumps([normalized.isoformat(), resource_id], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_cursor(raw: str | None) -> tuple[datetime | None, str | None]:
    """Decodifica un token de cursor. Devuelve ``(created_at, id)``.

    ``None``/token mal formado → ``(None, None)``, que la query interpreta
    como "primera página" (sin condición de corte).
    """
    if not raw:
        return None, None
    try:
        payload = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        normalized, resource_id = json.loads(payload)
        cursor_dt = datetime.fromisoformat(normalized)
        if cursor_dt.tzinfo is None:
            cursor_dt = cursor_dt.replace(tzinfo=UTC)
        return cursor_dt, resource_id
    except (ValueError, TypeError, json.JSONDecodeError):
        return None, None