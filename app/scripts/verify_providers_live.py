"""Canary script: live verification of AutoScout24 + mobile.de providers.

Usage (from project root, with env loaded):

    JWT_SECRET_KEY='test_secret_key_that_is_at_least_32_characters_long_xx' \
    ENVIRONMENT=test \
    python -m app.scripts.verify_providers_live

Exit codes:
  0 = at least AutoScout24 returned listings
  1 = both providers failed or AS24 returned 0
"""

from __future__ import annotations

import asyncio
import sys

from app.providers.autoscout24 import AutoScout24Provider
from app.providers.mobile_de import MobileDeProvider


async def _run() -> int:
    query = "BMW 320"
    limit = 5
    print(f"=== Live provider canary | query={query!r} limit={limit} ===\n")

    as24_ok = False
    mobile_ok = False

    # --- AutoScout24 ---
    try:
        provider = AutoScout24Provider()
        results = await provider.search(query=query, max_price=25000, country="DE", limit=limit)
        if results:
            as24_ok = True
            print(f"[AutoScout24] PASS — {len(results)} anuncios")
            for r in results[:3]:
                print(f"  • {r.title} | {r.price} EUR | {r.year} | {r.mileage_km} km | {r.url}")
        else:
            print("[AutoScout24] FAIL — 0 anuncios (selectores o bloqueo)")
    except Exception as exc:
        print(f"[AutoScout24] FAIL — {type(exc).__name__}: {exc}")

    print()

    # --- mobile.de ---
    try:
        provider = MobileDeProvider()
        results = await provider.search(query=query, max_price=25000, country="DE", limit=limit)
        if results:
            mobile_ok = True
            print(f"[mobile.de]   PASS — {len(results)} anuncios")
            for r in results[:3]:
                print(f"  • {r.title} | {r.price} EUR | {r.year} | {r.mileage_km} km | {r.url}")
        else:
            print("[mobile.de]   WARN — 0 anuncios (posible bloqueo suave)")
    except Exception as exc:
        # 403 is expected without residential proxy
        print(f"[mobile.de]   WARN (anti-bot) — {type(exc).__name__}: {exc}")

    print()
    if as24_ok:
        print("Resultado: AS24 operativo. mobile.de requiere proxy residencial si WARN.")
        return 0
    print("Resultado: AutoScout24 no devolvió datos — revisar parsers / red.")
    return 1


def main() -> None:
    code = asyncio.run(_run())
    sys.exit(code)


if __name__ == "__main__":
    main()
