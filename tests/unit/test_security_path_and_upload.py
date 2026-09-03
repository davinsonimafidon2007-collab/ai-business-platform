"""Tests de seguridad SEC.LFI.1 / SEC.UPLOAD.1 — path safety y uploads."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.path_safety import UnsafePhotoPathError, validate_photo_file_path
from app.services.photo_upload_validator import (
    InvalidImageUploadError,
    validate_image_upload,
)


@pytest.fixture()
def upload_dir(tmp_path: Path) -> Path:
    d = tmp_path / "uploads"
    (d / "sess-1").mkdir(parents=True)
    return d


class TestValidatePhotoFilePath:
    def test_ruta_dentro_de_uploads_ok(self, upload_dir: Path) -> None:
        p = str(upload_dir / "sess-1" / "foto.jpg")
        assert validate_photo_file_path(p, upload_dir) == p

    def test_traversal_fuera_de_uploads_bloqueado(self, upload_dir: Path) -> None:
        p = str(upload_dir / "sess-1" / ".." / ".." / "secret.env")
        with pytest.raises(UnsafePhotoPathError):
            validate_photo_file_path(p, upload_dir)

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/passwd",
            "/home/user/.ssh/id_rsa",
            "../.env",
        ],
    )
    def test_rutas_absolutas_sistema_bloqueadas(
        self, path: str, upload_dir: Path
    ) -> None:
        with pytest.raises(UnsafePhotoPathError):
            validate_photo_file_path(path, upload_dir)

    @pytest.mark.parametrize(
        "path",
        [
            "C:\\Windows\\win.ini",
            "\\\\servidor\\compartido\\secreto.png",
        ],
    )
    def test_rutas_windows_bloqueadas(self, path: str, upload_dir: Path) -> None:
        with pytest.raises(UnsafePhotoPathError):
            validate_photo_file_path(path, upload_dir)

    def test_https_publico_permitido(self, upload_dir: Path) -> None:
        import app.core.url_guard as guard

        guard._DNS_CACHE["cdn.example.com"] = (False, float("inf"))
        try:
            url = "https://cdn.example.com/fotos/auto.jpg"
            assert validate_photo_file_path(url, upload_dir) == url
        finally:
            guard._DNS_CACHE.pop("cdn.example.com", None)

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "data:image/png;base64,AAAA",
            "file:///etc/passwd",
            "http://127.0.0.1:8000/api/v1/health",
        ],
    )
    def test_urls_no_https_o_internas_bloqueadas(
        self, url: str, upload_dir: Path
    ) -> None:
        with pytest.raises(UnsafePhotoPathError):
            validate_photo_file_path(url, upload_dir)

    def test_vacio_rechazado(self, upload_dir: Path) -> None:
        with pytest.raises(UnsafePhotoPathError):
            validate_photo_file_path("", upload_dir)


def _jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"A" * 64


class TestValidateImageUpload:
    def test_jpeg_valido(self) -> None:
        assert validate_image_upload("foto.JPG", "image/jpeg", _jpeg()) == ".jpg"

    def test_content_type_no_imagen(self) -> None:
        with pytest.raises(InvalidImageUploadError):
            validate_image_upload("a.jpg", "text/html", _jpeg())

    def test_content_type_vacio_rechazado(self) -> None:
        # Antes un content_type vacío pasaba la validación del endpoint
        with pytest.raises(InvalidImageUploadError):
            validate_image_upload("a.jpg", None, _jpeg())

    def test_extension_peligrosa_bloqueada(self) -> None:
        for name in ("shell.php", "page.html", "vector.svg", "script.js", "x"):
            with pytest.raises(InvalidImageUploadError):
                validate_image_upload(name, "image/jpeg", _jpeg())

    def test_tamano_excedido(self) -> None:
        big = b"\xff\xd8\xff" + b"A" * 100
        with pytest.raises(InvalidImageUploadError):
            validate_image_upload("big.jpg", "image/jpeg", big, max_bytes=10)

    def test_magic_bytes_invalidos(self) -> None:
        with pytest.raises(InvalidImageUploadError):
            validate_image_upload(
                "falso.jpg", "image/jpeg", b"<html>no soy imagen</html>"
            )

    def test_png_y_webp_ok(self) -> None:
        png = b"\x89PNG\r\n\x1a\n" + b"B" * 16
        webp = b"RIFF\x24\x00\x00\x00WEBPVP8 "
        assert validate_image_upload("a.png", "image/png", png) == ".png"
        assert validate_image_upload("b.webp", "image/webp", webp) == ".webp"
