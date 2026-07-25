from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.logging import StructuredFormatter, get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Resetea la configuración de logging antes de cada test."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    yield
    root_logger.handlers.clear()


def test_setup_logging_development() -> None:
    """Verifica que setup_logging configura correctamente en desarrollo."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "development"
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)


def test_setup_logging_production() -> None:
    """Verifica que setup_logging configura correctamente en producción."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "production"
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, StructuredFormatter)


def test_get_logger_returns_logger() -> None:
    """Verifica que get_logger retorna un logger válido."""
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_structured_formatter_includes_request_id() -> None:
    """Verifica que el formateador estructurado incluye request_id."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "test-request-id-123"

    formatted = formatter.format(record)
    assert "test-request-id-123" in formatted
    assert "Test message" in formatted
    assert "INFO" in formatted


def test_structured_formatter_without_request_id() -> None:
    """Verifica que el formateador funciona sin request_id."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "Test message" in formatted
    assert "INFO" in formatted
    # No debe incluir request_id si no existe
    assert "request_id" not in formatted


def test_structured_formatter_with_exception() -> None:
    """Verifica que el formateador incluye excepciones."""
    formatter = StructuredFormatter()
    try:
        raise ValueError("Test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )

    formatted = formatter.format(record)
    assert "Error occurred" in formatted
    assert "ValueError" in formatted
    assert "Test error" in formatted


def test_structured_formatter_with_extra_data() -> None:
    """Verifica que el formateador incluye datos extra."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.extra = {"user_id": "123", "action": "login"}

    formatted = formatter.format(record)
    assert "Test message" in formatted
    assert "user_id" in formatted
    assert "123" in formatted
    assert "action" in formatted
    assert "login" in formatted