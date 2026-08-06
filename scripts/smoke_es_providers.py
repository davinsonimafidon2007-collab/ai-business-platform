#!/usr/bin/env python3
"""Smoke mercado ES (fixtures offline + AS24-ES opcional).

Exit codes:
  0 — OK
  1 — fallo de aserción / error inesperado
  2 — skip (live pedido pero flag off / provider ausente)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Asegurar importabilidad de `app` desde scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

AUTOSCOUT24_ES_SEARCH_URL = (
    "https://www.autoscout24.es/lst/bmw"
    "?atype=C&cy=E&desc=0&sort=standard&source=listpage_search-mask&ustate=N%2CU"
)


def _print_registry() -> int:
    from app.core.config import settings
    from app.providers.registry import ProviderRegistry

    ProviderRegistry.ensure_default_providers()
    names = ProviderRegistry.list_providers()
    print(f"profile={getattr(settings, 'default_import_cost_profile', None)}")
    print(f"providers={names}")
    print(f"enable_es_market_fixture={settings.enable_es_market_fixture}")
    print(f"enable_coches_net_fixture={settings.enable_coches_net_fixture}")
    print(f"enable_autoscout24_es={settings.enable_autoscout24_es}")
    return 0


async def _smoke_fixtures() -> int:
    from app.providers.coches_net_fixture import CochesNetFixtureProvider
    from app.providers.es_market_fixture import EsMarketFixtureProvider

    es = EsMarketFixtureProvider()
    cn = CochesNetFixtureProvider()
    q = "BMW 320"
    es_hits = await es.search(q)
    cn_hits = await cn.search(q)
    print(f"es_market_fixture search({q!r}) -> {len(es_hits)}")
    print(f"coches_net_fixture search({q!r}) -> {len(cn_hits)}")
    if len(es_hits) < 1:
        print("FAIL: es_market_fixture sin resultados", file=sys.stderr)
        return 1
    if len(cn_hits) < 1:
        print("FAIL: coches_net_fixture sin resultados", file=sys.stderr)
        return 1
    print("OK fixtures offline")
    return 0


async def _smoke_html_coches() -> int:
    from app.providers.coches_net_html import CochesNetHtmlFixtureProvider

    p = CochesNetHtmlFixtureProvider()
    hits = await p.search("")
    print(f"coches_net_html_fixture search('') -> {len(hits)}")
    if len(hits) < 1:
        print("FAIL: coches_net_html_fixture sin resultados", file=sys.stderr)
        return 1
    print("OK coches_net_html_fixture")
    return 0


async def _smoke_live_as24_es() -> int:
    from app.core.config import settings
    from app.providers.registry import ProviderRegistry

    ProviderRegistry.ensure_default_providers()
    if not settings.enable_autoscout24_es:
        print("SKIP: ENABLE_AUTOSCOUT24_ES=false")
        return 2
    if "autoscout24_es" not in ProviderRegistry.list_providers():
        print("SKIP: autoscout24_es no registrado")
        return 2
    provider = ProviderRegistry.get("autoscout24_es")
    try:
        # AutoScout24Provider.search() espera una URL de búsqueda (no texto libre).
        results = await provider.search(AUTOSCOUT24_ES_SEARCH_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL live autoscout24_es: {exc}", file=sys.stderr)
        return 1
    print(f"autoscout24_es search -> {len(results)} results")
    if len(results) < 1:
        print(
            "WARN: 0 results (anti-bot o query); se considera OK de conectividad si no hubo excepción",
        )
    print("OK live autoscout24_es (sin excepción)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke providers mercado ES")
    parser.add_argument("--registry", action="store_true", help="Print registry snapshot")
    parser.add_argument(
        "--live-as24-es",
        action="store_true",
        help="Try real AutoScout24 ES (requires ENABLE_AUTOSCOUT24_ES=true)",
    )
    parser.add_argument(
        "--skip-fixtures",
        action="store_true",
        help="Do not run offline fixture searches",
    )
    parser.add_argument(
        "--html-coches",
        action="store_true",
        help="Run offline Coches.net HTML fixture smoke (direct instantiation)",
    )
    args = parser.parse_args()

    if args.registry:
        return _print_registry()

    async def _run() -> int:
        code = 0
        if not args.skip_fixtures:
            code = await _smoke_fixtures()
            if code != 0:
                return code
        if args.html_coches:
            code = await _smoke_html_coches()
            if code != 0:
                return code
        if args.live_as24_es:
            live = await _smoke_live_as24_es()
            if live == 1:
                return 1
            if live == 2:
                return 2
        return 0

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
