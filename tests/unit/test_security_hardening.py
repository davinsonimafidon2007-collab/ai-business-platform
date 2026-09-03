"""TASK 8 — Endurecimiento de seguridad (AUD-023 / AUD-024).

- AUD-023: /docs, /redoc y /openapi.json no deben quedar públicos en
  producción por defecto.
- AUD-024: la subida de fotos de inspección no tenía límite de tamaño en
  servidor y validaba el tipo solo por lo que declaraba el cliente.
"""

from __future__ import annotations

import pytest

from app.api.v1.routes.inspection import (
    _detect_image_extension,
    _read_upload_within_limit,
)
from app.core.config import Settings, settings

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_GIF = b"GIF89a" + b"\x00" * 32
_WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32
_HEIC = b"\x00\x00\x00\x18" + b"ftyp" + b"heic" + b"\x00" * 32


def _make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "jwt_secret_key": "x" * 40,
        "environment": "development",
    }
    base.update(overrides)
    if base.get("environment") == "production":
        # Settings valida CORS en production (SEC-001): orígenes reales.
        base.setdefault("cors_origins", "https://app.ejemplo.com")
    # `_env_file=None`: el .env del desarrollador no debe decidir el resultado
    # de estos tests (p. ej. si tiene ENABLE_DOCS=true).
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


class TestDocsGating:
    """AUD-023: la documentación describe toda la superficie de la API."""

    def test_docs_enabled_in_development_by_default(self) -> None:
        assert _make_settings(environment="development").docs_enabled is True

    def test_docs_disabled_in_production_by_default(self) -> None:
        assert _make_settings(environment="production").docs_enabled is False

    def test_docs_can_be_forced_on_in_production(self) -> None:
        cfg = _make_settings(environment="production", enable_docs=True)
        assert cfg.docs_enabled is True

    def test_docs_can_be_forced_off_in_development(self) -> None:
        cfg = _make_settings(environment="development", enable_docs=False)
        assert cfg.docs_enabled is False

    def test_current_app_exposes_docs_only_when_enabled(self) -> None:
        """La app construida refleja la decisión (no queda cableado fijo)."""
        from app.main import app

        if settings.docs_enabled:
            assert app.docs_url == "/docs"
            assert app.openapi_url == "/openapi.json"
        else:  # pragma: no cover — depende del entorno de ejecución
            assert app.docs_url is None
            assert app.openapi_url is None


class TestImageMagicBytes:
    """AUD-024: el content_type lo elige el cliente; el contenido no."""

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (_JPEG, ".jpg"),
            (_PNG, ".png"),
            (_GIF, ".gif"),
            (_WEBP, ".webp"),
            (_HEIC, ".heic"),
        ],
    )
    def test_detects_supported_image_formats(
        self, content: bytes, expected: str
    ) -> None:
        assert _detect_image_extension(content) == expected

    def test_rejects_non_image_content(self) -> None:
        assert _detect_image_extension(b"<?php system($_GET['c']); ?>") is None

    def test_rejects_executable_disguised_as_image(self) -> None:
        """Un binario renombrado a .jpg no pasa la comprobación de contenido."""
        assert _detect_image_extension(b"MZ\x90\x00" + b"\x00" * 64) is None

    def test_rejects_empty_content(self) -> None:
        assert _detect_image_extension(b"") is None

    def test_rejects_truncated_riff_without_webp_marker(self) -> None:
        assert _detect_image_extension(b"RIFF" + b"\x00" * 8) is None


class _FakeUpload:
    """UploadFile mínimo que sirve un contenido en trozos."""

    def __init__(self, content: bytes) -> None:
        self._buffer = content
        self._pos = 0

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._buffer[self._pos :]
            self._pos = len(self._buffer)
            return chunk
        chunk = self._buffer[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


class TestUploadSizeLimit:
    """AUD-024: antes se leía el fichero entero en memoria sin ningún tope."""

    @pytest.mark.asyncio
    async def test_accepts_file_within_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "max_upload_size_mb", 1)
        content = _JPEG + b"\x00" * 1024
        result = await _read_upload_within_limit(_FakeUpload(content))
        assert result == content

    @pytest.mark.asyncio
    async def test_rejects_file_over_limit_with_413(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "max_upload_size_mb", 1)
        oversized = b"\x00" * (2 * 1024 * 1024)

        with pytest.raises(HTTPException) as exc:
            await _read_upload_within_limit(_FakeUpload(oversized))
        assert exc.value.status_code == 413

    @pytest.mark.asyncio
    async def test_rejects_empty_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "max_upload_size_mb", 1)
        with pytest.raises(HTTPException) as exc:
            await _read_upload_within_limit(_FakeUpload(b""))
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_limit_is_configurable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Con un límite mayor, el mismo fichero pasa."""
        from fastapi import HTTPException

        payload = b"\x00" * (2 * 1024 * 1024)

        monkeypatch.setattr(settings, "max_upload_size_mb", 1)
        with pytest.raises(HTTPException):
            await _read_upload_within_limit(_FakeUpload(payload))

        monkeypatch.setattr(settings, "max_upload_size_mb", 5)
        assert await _read_upload_within_limit(_FakeUpload(payload)) == payload
