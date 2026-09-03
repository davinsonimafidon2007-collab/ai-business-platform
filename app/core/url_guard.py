"""Guard SSRF (SEC.SSRF.1): solo URLs HTTP/HTTPS hacia hosts públicos.

Usado por ``ProviderHttpClient`` antes de construir cualquier petición a una
URL absoluta. Las rutas relativas no pasan por aquí: se resuelven contra la
``base_url`` de confianza del provider.

Reglas:
- Esquema limitado a http/https (bloquea file://, data:, ftp:, gopher:, ...).
- Bloquea literales IP internas: loopback (127.0.0.0/8, ::1), privadas
  (10/8, 172.16/12, 192.168/16), link-local incluida la metadata AWS
  (169.254.169.254), unspecified (0.0.0.0) y ``localhost`` en cualquier caso.
- Bloquea credenciales embebidas (``user:pass@host``).
- Hostnames: se resuelven por DNS con caché TTL corta
  (``_DNS_CACHE[host] = (es_privada, expira_epoch)``). Si algún IP resuelto
  es interno se bloquea. Si el DNS falla se permite pasar (fail-open): un
  nombre que no resuelve no puede ocultar una IP interna y el fallo real de
  conexión lo reportará httpx.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import urlsplit

_DNS_TTL_OK = 300.0
"""Segundos que se recuerda una resolución DNS correcta."""

_DNS_TTL_FAIL = 30.0
"""Segundos que se recuerda un fallo de DNS antes de reintentar."""

_DNS_CACHE: dict[str, tuple[bool, float]] = {}
"""host -> (alguna_ip_es_interna, expira_epoch). Expuesto para tests."""


class UnsafeURLError(ValueError):
    """La URL apunta a un destino no permitido (SSRF o esquema peligroso)."""


def _host_is_internal_literal(host: str) -> bool | None:
    """True si ``host`` es un literal IP interno; None si no es un literal IP."""
    candidate = host.strip("[]")
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return not ip.is_global


def _resolve_host_is_internal(host: str) -> bool:
    """Resuelve ``host`` y dice si alguna IP es interna.

    Con caché TTL. Fallo de DNS -> False (fail-open, ver docstring del módulo).
    """
    now = time.time()
    cached = _DNS_CACHE.get(host)
    if cached is not None and cached[1] > now:
        return cached[0]

    internal = False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        internal = False
        _DNS_CACHE[host] = (internal, now + _DNS_TTL_FAIL)
        return internal

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not ip.is_global:
            internal = True
            break
    _DNS_CACHE[host] = (internal, now + _DNS_TTL_OK)
    return internal


def ensure_public_http_url(url: str) -> str:
    """Valida que ``url`` sea http(s) hacia un host público y la devuelve intacta.

    Lanza :class:`UnsafeURLError` si no lo es. Nunca reescribe la URL: solo
    acepta o rechaza.
    """
    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        raise UnsafeURLError(f"URL malformada: {url!r}") from exc

    if parts.scheme.lower() not in {"http", "https"}:
        raise UnsafeURLError(
            f"Esquema no permitido: {parts.scheme!r} (solo http/https)"
        )

    hostname = parts.hostname
    if not hostname:
        raise UnsafeURLError(f"URL sin hostname: {url!r}")

    if "@" in (parts.netloc or ""):
        raise UnsafeURLError(
            f"Credenciales embebidas no permitidas en la URL: {url!r}"
        )

    if hostname.lower() == "localhost":
        raise UnsafeURLError(f"Host interno bloqueado: {hostname!r}")

    literal = _host_is_internal_literal(hostname)
    if literal is True:
        raise UnsafeURLError(f"IP interna bloqueada: {hostname!r}")
    if literal is None and _resolve_host_is_internal(hostname):
        raise UnsafeURLError(f"Hostname resuelve a IP interna: {hostname!r}")

    return url
