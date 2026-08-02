#!/usr/bin/env python3
"""Verificación en vivo de parsers mobile.de y AutoScout24.

Uso (desde la raíz del repo, con deps instaladas):

    uv run python -m app.scripts.verify_providers_live
    # o
    python app/scripts/verify_providers_live.py

Sale con código 0 si al menos AutoScout24 devuelve anuncios parseados.
mobile.de puede fallar por anti-bot (403); se reporta como WARN, no como
fallo fatal, hasta que haya proxy.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Permitir ejecución directa sin instalar el paquete
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.autoscout24 import AutoScout24Provider
from app.providers.mobile_de import MobileDeProvider
from app.providers.exceptions import ProviderConnectionError, ProviderError

AS24_SEARCH_URL = (
    "https://www.autoscout24.de/lst"
    "?atype=C&cy=D&desc=0&sortage=age&ustate=N%2CU"
)
MOBILE_SEARCH_URL = (
    "https://suchen.mobile.de/fahrzeuge/search.html"
    "?dam=false&isSearchRequest=true&ref=srp&sb=rel&vc=Car"
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
        return False, "0 anuncios parseados (selectores/JSON rotos o página vacía)"

    sample = results[0]
    fields = {
        "external_id": sample.external_id,
        "brand": sample.brand,
        "model": sample.model,
        "price": sample.price,
        "mileage": sample.mileage,
        "year": sample.year,
        "url": sample.url,
    }
    missing = [k for k, v in fields.items() if v in (None, "", [])]
    detail = (
        f"{len(results)} anuncios | ejemplo: "
        f"{sample.brand} {sample.model} {sample.price}€ "
        f"km={sample.mileage} year={sample.year} id={sample.external_id}"
    )
    if missing:
        detail += f" | campos vacíos en 1º: {missing}"
    # Éxito si hay resultados y al menos id + price o brand
    ok = bool(sample.external_id) and (
        sample.price is not None or sample.brand is not None
    )
    return ok, detail


async def check_mobile_de() -> tuple[str, str]:
    """Devuelve (status, detail) donde status es ok|blocked|fail."""
    provider = MobileDeProvider()
    try:
        results = await provider.search(MOBILE_SEARCH_URL)
    except ProviderConnectionError as exc:
        return "blocked", str(exc)
    except ProviderError as exc:
        return "fail", f"ERROR provider: {exc}"
    except Exception as exc:  # noqa: BLE001
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
    print("=== Verificación en vivo de providers ===\n")

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
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
