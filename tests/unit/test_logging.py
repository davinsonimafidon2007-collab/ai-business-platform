from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

from app.core.logging import StructuredFormatter, get_logger, get_logging_config, setup_logging


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
        mock_settings.log_level = "DEBUG"
        mock_settings.log_json = False
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)


def test_setup_logging_production() -> None:
    """Verifica que setup_logging configura correctamente en producción."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "production"
        mock_settings.log_level = "INFO"
        mock_settings.log_json = False  # production forces JSON
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, StructuredFormatter)


def test_setup_logging_with_custom_log_level() -> None:
    """Verifica que setup_logging respeta log_level de configuración."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "test"
        mock_settings.log_level = "WARNING"
        mock_settings.log_json = False
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING


def test_get_logger_returns_logger() -> None:
    """Verifica que get_logger retorna un logger válido."""
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_structured_formatter_includes_request_id() -> None:
    """Verifica que el formateador estructurado incluye request_id."""
    formatter = StructuredFormatter(json_output=True)
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
    data = json.loads(formatted)
    assert data["request_id"] == "test-request-id-123"
    assert data["message"] == "Test message"
    assert data["level"] == "INFO"


def test_structured_formatter_without_request_id() -> None:
    """Verifica que el formateador funciona sin request_id."""
    formatter = StructuredFormatter(json_output=True)
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
    data = json.loads(formatted)
    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert "request_id" not in data


def test_structured_formatter_with_exception() -> None:
    """Verifica que el formateador incluye excepciones."""
    formatter = StructuredFormatter(json_output=True)
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
    data = json.loads(formatted)
    assert data["message"] == "Error occurred"
    assert "ValueError" in data["exception"]
    assert "Test error" in data["exception"]


def test_structured_formatter_with_extra_data() -> None:
    """Verifica que el formateador incluye datos extra."""
    formatter = StructuredFormatter(json_output=True)
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
    data = json.loads(formatted)
    assert data["message"] == "Test message"
    assert data["user_id"] == "123"
    assert data["action"] == "login"


def test_structured_formatter_includes_correlation_id() -> None:
    """Verifica que el formateador incluye correlation_id."""
    formatter = StructuredFormatter(json_output=True)
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "corr-123"

    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["correlation_id"] == "corr-123"


def test_structured_formatter_non_json() -> None:
    """Verifica que el formateador sin JSON produce string legible."""
    formatter = StructuredFormatter(json_output=False)
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
    assert isinstance(formatted, str)
    assert "Test message" in formatted


def test_get_logging_config() -> None:
    """Verifica que get_logging_config devuelve configuración."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.log_level = "DEBUG"
        mock_settings.log_json = True
        mock_settings.log_request_body = True
        mock_settings.log_response_body = False
        mock_settings.max_log_body_size = 2048
        mock_settings.enable_access_log = True
        mock_settings.environment = "test"

        config = get_logging_config()
        assert config["log_level"] == "DEBUG"
        assert config["log_json"] is True
        assert config["log_request_body"] is True
        assert config["max_log_body_size"] == 2048
        assert config["enable_access_log"] is True


def test_setup_logging_with_json_true() -> None:
    """Verifica que LOG_JSON=True produce formato JSON."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "development"
        mock_settings.log_level = "INFO"
        mock_settings.log_json = True
        setup_logging()

        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)


def test_setup_logging_log_level_case_insensitive() -> None:
    """Verifica que el nivel de log es case-insensitive."""
    with patch("app.core.logging.settings") as mock_settings:
        mock_settings.environment = "test"
        mock_settings.log_level = "debug"
        mock_settings.log_json = False
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


def test_logger_extra_fields_preserved() -> None:
    """Verifica que campos extra en el logger se preservan en JSON."""
    formatter = StructuredFormatter(json_output=True)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="test.py", lineno=1,
        msg="msg", args=(), exc_info=None,
    )
    record.extra = {"duration_ms": 150.5, "status_code": 200}

    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["duration_ms"] == 150.5
    assert data["status_code"] == 200

