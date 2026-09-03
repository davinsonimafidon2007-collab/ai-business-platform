"""Path safety para fotos de inspección (SEC.LFI.1 / SEC.UPLOAD.1).

``validate_photo_file_path`` es la única puerta de entrada de ``file_path``
en ``InspectionService.upload_photo``:

- URLs: solo **https** hacia hosts públicos (delega en ``url_guard``, que
  bloquea SSRF/localhost/IPs internas). Devuelve la URL intacta.
- Rutas de fichero: deben resolver DENTRO del directorio de uploads del
  servidor. Bloquea traversal (``..``), rutas absolutas del sistema
  (``/etc/passwd``, ``C:\\Windows\\..``) y UNC (``\\\\servidor\\share``).
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.url_guard import UnsafeURLError, ensure_public_http_url


class UnsafePhotoPathError(ValueError):
    """El ``file_path`` escapa del directorio de uploads o es una URL insegura."""


_URL_WITH_AUTHORITY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_BARE_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")


def _looks_like_url(path: str) -> bool:
    if _URL_WITH_AUTHORITY_RE.match(path):
        return True
    if _WINDOWS_DRIVE_RE.match(path):
        return False
    # Esquemas sin autoridad (data:, mailto:) — un solo carácter es una
    # unidad de Windows, no un esquema.
    match = _BARE_SCHEME_RE.match(path)
    return bool(match and len(match.group(1)) > 1)


def validate_photo_file_path(file_path: str, upload_dir: str | Path) -> str:
    """Valida ``file_path`` (ruta o URL) contra ``upload_dir``.

    Devuelve el valor original si es seguro; lanza
    :class:`UnsafePhotoPathError` en caso contrario.
    """
    if not file_path or not file_path.strip():
        raise UnsafePhotoPathError("file_path vacío")

    if _looks_like_url(file_path):
        # Solo https público: http sería descarga en claro y posible SSRF.
        if not file_path.lower().startswith("https://"):
            raise UnsafePhotoPathError(
                f"Solo se permiten URLs https públicas: {file_path!r}"
            )
        try:
            return ensure_public_http_url(file_path)
        except UnsafeURLError as exc:
            raise UnsafePhotoPathError(str(exc)) from exc

    base = Path(upload_dir).resolve()
    candidate = Path(file_path)
    # Las rutas absolutas (/etc/passwd, C:\Windows\win.ini, UNC) nunca están
    # dentro de upload_dir; las relativas se resuelven contra él.
    resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise UnsafePhotoPathError(
            f"file_path escapa del directorio de uploads: {file_path!r}"
        ) from exc
    return file_path
