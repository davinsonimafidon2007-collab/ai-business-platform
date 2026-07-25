from __future__ import annotations

import logging
import sys
from typing import Any

from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Formateador de logs estructurados en JSON."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

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

        # Añadir excepción si existe
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir datos extra si existen
        extra = getattr(record, "extra", None)
        if extra:
            log_data.update(extra)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """Configura el sistema de logging estructurado."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if settings.environment == "production" else logging.DEBUG)

    # Remover handlers existentes
    root_logger.handlers.clear()

    # Handler para consola (Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if settings.environment == "production" else logging.DEBUG)

    # Usar formato estructurado en producción, formato legible en desarrollo
    if settings.environment == "production":
        console_handler.setFormatter(StructuredFormatter())
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
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre especificado."""
    return logging.getLogger(name)