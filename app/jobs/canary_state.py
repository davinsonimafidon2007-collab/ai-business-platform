"""Último resultado del ProviderCanaryJob (proceso local).

Holder mínimo en memoria para que el endpoint admin /status pueda exponer
si AS24 / mobile.de están sanos según la última ejecución del canary,
sin necesidad de leer logs ni persistir en DB.

Reiniciar el proceso → ``None`` hasta el próximo canary.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

_lock = threading.Lock()
_last: dict[str, Any] | None = None


def set_last_canary_result(
    *,
    success: bool,
    message: str,
    data: dict[str, Any],
) -> None:
    """Almacena el último resultado del canary (thread-safe)."""
    global _last
    with _lock:
        _last = {
            "success": success,
            "message": message,
            "data": data,
            "finished_at": datetime.now(UTC).isoformat(),
        }


def get_last_canary_result() -> dict[str, Any] | None:
    """Devuelve una copia del último resultado, o ``None`` si aún no hay."""
    with _lock:
        return None if _last is None else dict(_last)