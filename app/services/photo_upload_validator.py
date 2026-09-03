"""Validación de uploads de imagen (SEC.UPLOAD.1).

Valida nombre, content-type, tamaño y magic bytes ANTES de persistir nada.
Devuelve la extensión canónica con la que debe guardarse el fichero, de modo
que la extensión final depende del contenido real, no del nombre enviado.
"""

from __future__ import annotations

from pathlib import Path

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024

_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

_MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)
"""Prefijos magic bytes -> extensión canónica. WebP se detecta aparte."""


class InvalidImageUploadError(ValueError):
    """El upload no es una imagen válida (tipo, extensión, tamaño o contenido)."""


def _detect_canonical_ext(data: bytes) -> str | None:
    for prefix, ext in _MAGIC_SIGNATURES:
        if data.startswith(prefix):
            return ext
    # RIFF....WEBP: 'WEBP' en offset 8.
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def validate_image_upload(
    file_name: str,
    content_type: str | None,
    data: bytes,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> str:
    """Valida un upload de imagen y devuelve su extensión canónica.

    Lanza :class:`InvalidImageUploadError` si el nombre lleva extensión no
    permitida (o ninguna), el content-type no es ``image/*``, el cuerpo
    excede ``max_bytes`` o los magic bytes no corresponden a una imagen real
    coherente con la extensión declarada.
    """
    if not content_type or not content_type.lower().startswith("image/"):
        raise InvalidImageUploadError(
            f"content_type no es de imagen: {content_type!r}"
        )

    if max_bytes > 0 and len(data) > max_bytes:
        raise InvalidImageUploadError(
            f"Imagen demasiado grande: {len(data)} bytes > {max_bytes}"
        )

    ext = Path(file_name or "").suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise InvalidImageUploadError(
            f"Extensión no permitida: {ext!r} (permitidas: {sorted(_ALLOWED_EXTS)})"
        )

    canonical = _detect_canonical_ext(data)
    if canonical is None:
        raise InvalidImageUploadError("El contenido no son magic bytes de imagen válida")

    expected = ".jpg" if ext in {".jpg", ".jpeg"} else ext
    if canonical != expected:
        raise InvalidImageUploadError(
            f"Extensión {ext!r} no coincide con el contenido ({canonical!r})"
        )
    return canonical
