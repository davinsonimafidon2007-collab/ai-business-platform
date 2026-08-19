from __future__ import annotations

from typing import Any


def get_actionable_message(issue: Any) -> str:
    """Devuelve un mensaje accionable para un ProviderIssue."""
    error_type = getattr(issue, "error_type", "") or ""
    message = getattr(issue, "message", "") or ""
    provider = getattr(issue, "provider", "proveedor") or "proveedor"

    if "not_found" in error_type.lower() or "404" in message or "not found" in message.lower():
        return f"Revisa la marca y el modelo ingresados; {provider} no encontró coincidencia."
    if "anti_bot" in error_type.lower() or "403" in message or "forbidden" in message.lower() or "anti-bot" in message.lower():
        return f"Verifica la configuración de proxy; {provider} bloqueó la petición por detección anti-bot."
    if "timeout" in error_type.lower():
        return f"Revisa tu conexión a red o inténtalo más tarde; {provider} no respondió a tiempo."

    return f"Revisa la búsqueda en {provider}: {message or 'Ocurrió un error inesperado.'}"
