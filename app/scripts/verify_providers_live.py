#!/usr/bin/env python3
"""Verificación en vivo de parsers mobile.de y AutoScout24 (Task 1b).

Compatible con la arquitectura real:
  - VehicleProvider.search(url: str)  → lista de VehicleSearchResult
  - DTOs en app.providers.dto
  - HTTP vía ProviderHttpClient

Uso:

    export JWT_SECRET_KEY='test_secret_key_that_is_at_least_32_characters_long_xx'
    export ENVIRONMENT=test
    uv run python -m app.scripts.verify_providers_live

Códigos de salida:
  0 = AutoScout24 devolvió anuncios parseados (PASS)
  1 = AutoScout24 falló o devolvió 0 anuncios (FAIL)

mobile.de en 403 anti-bot → WARN (no falla el exit code).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.autoscout24 import AutoScout24Provider
from app.providers.exceptions import ProviderConnectionError, ProviderError
from app.providers.mobile_de import MobileDeProvider

AS24_SEARCH_URL = (
    "https://www.autoscout24.de/lst"
    "?atype=C&cy=D&desc=0&sort=standard&ustate=N%2CU"
    "&q=BMW+320&pricefrom=0&priceto=25000"
)
MOBILE_SEARCH_URL = (
    "https://suchen.mobile.de/fahrzeuge/search.html"
    "?dam=false&isSearchRequest=true&ref=srp&sb=rel&vc=Car"
    "&ms=3500%3B9%3B%3B%3B&cn=DE"
)


async def check_autoscout24() -> tuple[bool, str]:
    provider = AutoScout24Provider()
    try:
        results = await provider.search(AS24_SEARCH_URL)
    except ProviderError as exc:
        return False, f"ERROR provider: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"ERROR inesperado: {type(exc).__name__}: {exc}"
    finally:
        await provider.close()

    if not results:
        return False, "0 anuncios parseados (selectores/JSON rotos, bloqueo o página vacía)"

    sample = results[0]
    detail = (
        f"{len(results)} anuncios | ejemplo: "
        f"{sample.brand} {sample.model} {sample.price}€ "
        f"km={sample.mileage} year={sample.year} id={sample.external_id}"
    )
    missing = [
        k
        for k, v in {
            "external_id": sample.external_id,
            "brand": sample.brand,
            "price": sample.price,
        }.items()
        if v in (None, "", [])
    ]
    if missing:
        detail += f" | campos vacíos en 1º: {missing}"

    ok = bool(sample.external_id) and (
        sample.price is not None or sample.brand is not None
    )
    return ok, detail


async def check_mobile_de() -> tuple[str, str]:
    """status: ok | blocked | fail"""
    provider = MobileDeProvider()
    try:
        results = await provider.search(MOBILE_SEARCH_URL)
    except ProviderConnectionError as exc:
        return "blocked", str(exc)
    except ProviderError as exc:
        return "fail", f"ERROR provider: {exc}"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "403" in msg or "Access denied" in msg:
            return "blocked", msg
        return "fail", f"ERROR inesperado: {type(exc).__name__}: {exc}"
    finally:
        await provider.close()

    if not results:
        return "fail", "0 anuncios parseados"
    sample = results[0]
    return (
        "ok",
        f"{len(results)} anuncios | ejemplo: "
        f"{sample.brand} {sample.model} {sample.price}€ id={sample.external_id}",
    )


async def main() -> int:
    print("=== Verificación en vivo de providers (Task 1b) ===\n")

    as24_ok, as24_detail = await check_autoscout24()
    print(f"[AutoScout24] {'PASS' if as24_ok else 'FAIL'} — {as24_detail}")

    mobile_status, mobile_detail = await check_mobile_de()
    label = {"ok": "PASS", "blocked": "WARN (anti-bot)", "fail": "FAIL"}[mobile_status]
    print(f"[mobile.de]   {label} — {mobile_detail}")

    print()
    if as24_ok:
        print("Resultado global: OK (AS24 operativo).")
        if mobile_status != "ok":
            print(
                "Pendiente: mobile.de requiere proxy/cookies — "
                "siguiente subtarea de la Fase A (anti-bot)."
            )
        return 0

    print("Resultado global: FAIL — AutoScout24 no devolvió datos útiles.")
    print(
        "Causas típicas: IP bloqueada, HTML distinto al esperado, "
        "o el provider de GitHub aún es la versión standalone incompatible."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
