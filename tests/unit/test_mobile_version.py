"""Tests para el endpoint de versión móvil (MOB-P3-002)."""

from __future__ import annotations

from unittest.mock import patch

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mobile_version_returns_defaults_without_env() -> None:
    """Sin env vars, devuelve 1.0.0 y la URL por defecto."""
    with patch.dict("os.environ", {}, clear=False):
        for key in (
            "MOBILE_MIN_VERSION",
            "MOBILE_LATEST_VERSION",
            "MOBILE_UPDATE_URL",
        ):
            os.environ.pop(key, None)
        response = client.get("/api/v1/mobile/version")
    assert response.status_code == 200
    body = response.json()
    assert body["min_version"] == "1.0.0"
    assert body["latest_version"] == "1.0.0"
    assert body["update_url"].endswith(
        "/ai-business-platform/releases"
    )


def test_mobile_version_reads_env_vars() -> None:
    """Lee las variables de entorno correctamente."""
    env = {
        "MOBILE_MIN_VERSION": "2.0.0",
        "MOBILE_LATEST_VERSION": "3.1.4",
        "MOBILE_UPDATE_URL": "https://example.com/update",
    }
    with patch.dict("os.environ", env, clear=False):
        response = client.get("/api/v1/mobile/version")
    assert response.status_code == 200
    body = response.json()
    assert body["min_version"] == "2.0.0"
    assert body["latest_version"] == "3.1.4"
    assert body["update_url"] == "https://example.com/update"
