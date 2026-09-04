"""Mensajes en español para fallos de providers (SEARCH.DIAG.1).

El resto de la UI ya muestra labels ES (REC.1, PROFIT.1, SEARCH.EMPTY.1); los
avisos de provider caído siguen el mismo criterio en vez de enseñar el
``repr`` de una excepción de Python al usuario.
"""

from __future__ import annotations

from typing import Any

# Excepciones de dominio → mensaje accionable.
_ERROR_MESSAGES_ES: dict[str, str] = {
    "ProviderConnectionError": (
        "{provider}: la fuente bloqueó la petición o no respondió. "
        "Suele ser anti-bot; con mobile.de es lo esperado sin proxy."
    ),
    "ProviderTimeoutError": (
        "{provider}: la fuente tardó demasiado en responder. "
        "Vuelve a intentarlo en unos minutos."
    ),
    "ProviderRateLimitError": (
        "{provider}: demasiadas peticiones seguidas (rate limit). "
        "Espera unos minutos antes de repetir la búsqueda."
    ),
    "ProviderParsingError": (
        "{provider}: no se pudo completar la búsqueda con esta fuente "
        "(puede que la web haya cambiado de formato, o que este tipo de "
        "búsqueda no esté soportado aún en este proveedor)."
    ),
    "ProviderMaxRetriesExceededError": (
        "{provider}: la fuente falló repetidamente y se agotaron los reintentos."
    ),
    "ProviderNotFoundError": (
        "{provider}: no existe esa búsqueda (HTTP 404). "
        "Revisa la marca o el modelo; puede que no estén en esa web."
    ),
    "HTTPStatusError": (
        "{provider}: la fuente devolvió un error HTTP. "
        "Puede que la URL de búsqueda ya no sea válida."
    ),
    "KeyError": "{provider}: proveedor no disponible en esta instalación.",
}

_STAGE_MESSAGES_ES: dict[str, str] = {
    "registry": "{provider}: proveedor no registrado; se ha omitido.",
    "search": "{provider}: no se pudieron obtener anuncios.",
    "analyze": "{provider}: un anuncio no se pudo analizar y se ha omitido.",
}

_FALLBACK_ES = "{provider}: error inesperado al consultar la fuente."


def provider_issue_message_es(
    *, provider: str, stage: str, error_type: str
) -> str:
    """Devuelve el mensaje ES de un fallo de provider.

    Prioriza el tipo de excepción (más informativo) y cae al stage si el
    error no está mapeado, de modo que nunca se muestra un mensaje vacío.
    """
    template = _ERROR_MESSAGES_ES.get(error_type)
    if template is None:
        template = _STAGE_MESSAGES_ES.get(stage, _FALLBACK_ES)
    return template.format(provider=provider)


def build_provider_issue_payloads(issues: Any) -> list[dict[str, Any]]:
    """Convierte ``ProviderIssue`` de dominio en dicts listos para la API."""
    payloads: list[dict[str, Any]] = []
    for issue in issues or []:
        provider = getattr(issue, "provider", "desconocido")
        stage = getattr(issue, "stage", "search")
        error_type = getattr(issue, "error_type", "Exception")
        payloads.append(
            {
                "provider": provider,
                "stage": stage,
                "error_type": error_type,
                "message": getattr(issue, "message", "") or error_type,
                "message_es": provider_issue_message_es(
                    provider=provider, stage=stage, error_type=error_type
                ),
                "external_id": getattr(issue, "external_id", None),
            }
        )
    return payloads
