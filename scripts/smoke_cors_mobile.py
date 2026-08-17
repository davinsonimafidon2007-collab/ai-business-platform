"""Smoke: CORS para orígenes móviles (MOB-P1-002).

Valida que la API devuelve los headers CORS correctos para los orígenes de
la app Capacitor (`capacitor://localhost`, `ionic://localhost`), de modo que
la WebView nativa de Android/iOS pueda llamar a la API sin bloqueos.

Uso:
  set BASE_URL=http://localhost:8000
  python scripts/smoke_cors_mobile.py

Exit 0 = OK; 1 = fallo de aserción/header; 2 = setup (API caída).
"""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"

MOBILE_ORIGINS = [
    "capacitor://localhost",
    "ionic://localhost",
]


def die(code: int, msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def check_preflight(c: httpx.Client, origin: str) -> None:
    """OPTIONS a un endpoint protegido con headers de preflight CORS."""
    r = c.options(
        "/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    allow_origin = r.headers.get("access-control-allow-origin")
    allow_headers = (r.headers.get("access-control-allow-headers") or "").lower()
    allow_methods = (r.headers.get("access-control-allow-methods") or "").upper()

    if allow_origin is None or origin not in allow_origin:
        die(
            1,
            f"{origin}: preflight no refleja el origin "
            f"(allow-origin={allow_origin!r}, status={r.status_code})",
        )
    # Los preflights legítimos son 200; FastAPI CORSMiddleware devuelve 200.
    if r.status_code != 200:
        die(1, f"{origin}: preflight → {r.status_code}")
    if "authorization" not in allow_headers:
        die(1, f"{origin}: allow-headers sin 'authorization' (got {allow_headers!r})")
    if "GET" not in allow_methods:
        die(1, f"{origin}: allow-methods sin GET (got {allow_methods!r})")
    print(f"OK: preflight {origin} → 200 (allow-origin={allow_origin!r})")


def check_simple_request(c: httpx.Client, origin: str) -> None:
    """GET /health con Origin móvil: debe incluir allow-origin en la respuesta."""
    r = c.get(f"{BASE}/health", headers={"Origin": origin})
    allow_origin = r.headers.get("access-control-allow-origin")
    if r.status_code != 200:
        die(1, f"{origin}: GET /health → {r.status_code}")
    if allow_origin is None or origin not in allow_origin:
        die(1, f"{origin}: /health sin allow-origin (got {allow_origin!r})")
    print(f"OK: GET /health con Origin {origin} → 200 (allow-origin={allow_origin!r})")


def main() -> None:
    try:
        r = httpx.get(f"{BASE}/health", timeout=5.0)
    except httpx.HTTPError as e:
        die(2, f"API no responde en {BASE}: {e}")
    if r.status_code != 200:
        die(2, f"/health → {r.status_code}")

    with httpx.Client(base_url=API, timeout=15.0) as c:
        for origin in MOBILE_ORIGINS:
            check_preflight(c, origin)
            check_simple_request(c, origin)

    print("OK: smoke CORS móvil passed")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
