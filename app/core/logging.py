from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


# Mapping of string level names to numeric levels
_LOG_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _resolve_log_level(level_name: str) -> int:
    """Resolve a log level name (case-insensitive) to its numeric value."""
    return _LOG_LEVEL_MAP.get(level_name.upper(), logging.INFO)


def _truncate_string(value: str, max_size: int) -> str:
    """Truncate a string if it exceeds max_size, appending a notice."""
    if len(value) > max_size:
        return value[:max_size] + f"... (truncated, original {len(value)} chars)"
    return value


class StructuredFormatter(logging.Formatter):
    """Formateador de logs estructurados en JSON."""

    def __init__(self, fmt: str | None = None, datefmt: str | None = None, *, json_output: bool = False) -> None:
        super().__init__(fmt, datefmt)
        self._json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Añadir request_id si existe en el contexto
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id

        # Añadir correlation_id si existe en el contexto
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Añadir excepción si existe
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir datos extra si existen
        extra = getattr(record, "extra", None)
        if extra:
            log_data.update(extra)

        if self._json_output:
            return json.dumps(log_data, ensure_ascii=False, default=str)

        # Fallback to readable format when not in JSON mode
        parts = [f"[{log_data['timestamp']}]", f"{log_data['level']:7}", f"{log_data['module']:30}", log_data["message"]]
        if request_id:
            parts.insert(1, f"rid={request_id}")
        return " ".join(parts)


def setup_logging() -> None:
    """Configura el sistema de logging estructurado según la configuración."""
    root_logger = logging.getLogger()
    root_logger.setLevel(_resolve_log_level(settings.log_level))

    # Remover handlers existentes
    root_logger.handlers.clear()

    # Handler para consola (Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_resolve_log_level(settings.log_level))

    # Determinar si usar formato JSON
    use_json = settings.log_json or settings.environment == "production"

    if use_json:
        console_handler.setFormatter(StructuredFormatter(json_output=True))
    else:
        # Formato legible para desarrollo
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(console_handler)

    # Reducir verbosidad de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre especificado."""
    return logging.getLogger(name)


def get_logging_config() -> dict[str, Any]:
    """Retorna un diccionario con la configuración actual de logging.

    Útil para diagnosticar y verificar configuración.
    """
    return {
        "log_level": settings.log_level,
        "log_json": settings.log_json or settings.environment == "production",
        "log_request_body": settings.log_request_body,
        "log_response_body": settings.log_response_body,
        "max_log_body_size": settings.max_log_body_size,
        "enable_access_log": settings.enable_access_log,
        "environment": settings.environment,
    }

