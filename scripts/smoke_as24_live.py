#!/usr/bin/env python3
"""Smoke live de AutoScout24 DE — fuente principal (SMOKE.AS24.LIVE.1).

Comprueba que AS24 sigue devolviendo listings parseables. Es el smoke que
importa para el uso personal: si esto falla, la app no encuentra coches.

No toca mobile.de (opcional, 403 esperado sin proxy) ni providers ES.

Exit codes:
  0 — OK, al menos 1 listing parseado
  1 — 0 listings (parser/DOM roto) o error de red/parse

Uso::

    uv run python scripts/smoke_as24_live.py
    uv run python scripts/smoke_as24_live.py --json
    uv run python scripts/smoke_as24_live.py --timeout 30
    uv run python scripts/smoke_as24_live.py --url "https://www.autoscout24.de/lst/bmw?..."

Depende de red real: **no** usar como gate de CI (AS24 puede aplicar
rate-limit). En CI corren los tests con mocks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Asegurar importabilidad de `app` desde scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Misma URL que ProviderCanaryJob: si una se rompe, la otra también.
DEFAULT_SEARCH_URL = (
    "https://www.autoscout24.de/lst"
    "?atype=C&cy=D&desc=0&sortage=age&ustate=N%2CU"
)


async def _run_smoke(url: str, timeout: float) -> tuple[int, dict[str, Any]]:
    """Ejecuta una búsqueda en AS24. Devuelve (exit_code, payload)."""
    from app.providers.autoscout24 import AutoScout24Provider
    from app.providers.exceptions import (
        ProviderConnectionError,
        ProviderError,
        ProviderRateLimitError,
        ProviderTimeoutError,
    )
    from app.providers.http_client import ProviderHttpClient

    client = ProviderHttpClient(
        provider_name="autoscout24",
        base_url="https://www.autoscout24.de",
        timeout=timeout,
    )
    provider = AutoScout24Provider(http_client=client)

    payload: dict[str, Any] = {"provider": "autoscout24", "url": url}
    started = time.perf_counter()

    try:
        results = await provider.search(url)
    except ProviderRateLimitError as exc:
        payload |= {
            "status": "rate_limited",
            "count": 0,
            "error": str(exc),
            "hint": "AS24 aplicó rate-limit. Reintenta en unos minutos.",
        }
        return 1, payload
    except ProviderTimeoutError as exc:
        payload |= {
            "status": "timeout",
            "count": 0,
            "error": str(exc),
            "hint": f"Sin respuesta en {timeout}s. Prueba --timeout mayor.",
        }
        return 1, payload
    except ProviderConnectionError as exc:
        payload |= {
            "status": "blocked",
            "count": 0,
            "error": str(exc),
            "hint": "Conexión rechazada o anti-bot. Revisa la red.",
        }
        return 1, payload
    except ProviderError as exc:
        payload |= {"status": "error", "count": 0, "error": str(exc)}
        return 1, payload
    except Exception as exc:  # noqa: BLE001
        # Sin traceback crudo: el mensaje debe bastar para ops.
        payload |= {
            "status": "error",
            "count": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
        return 1, payload
    finally:
        await provider.close()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    count = len(results) if results else 0
    payload |= {"count": count, "elapsed_ms": elapsed_ms}

    if count == 0:
        payload |= {
            "status": "fail",
            "hint": (
                "0 listings con HTTP OK: probable drift de selectores/DOM. "
                "Revisa app/providers/autoscout24.py."
            ),
        }
        return 1, payload

    first = results[0]
    payload |= {
        "status": "ok",
        "sample": {
            "external_id": getattr(first, "external_id", None),
            "brand": getattr(first, "brand", None),
            "model": getattr(first, "model", None),
            "price": getattr(first, "price", None),
            "year": getattr(first, "year", None),
        },
    }
    return 0, payload


def _print_human(payload: dict[str, Any], exit_code: int) -> None:
    status = payload.get("status", "?")
    count = payload.get("count", 0)

    if exit_code == 0:
        sample = payload.get("sample") or {}
        print(f"OK autoscout24: {count} listings ({payload.get('elapsed_ms')}ms)")
        print(
            "  sample: id={id} {brand} {model} price={price} year={year}".format(
                id=sample.get("external_id"),
                brand=sample.get("brand"),
                model=sample.get("model"),
                price=sample.get("price"),
                year=sample.get("year"),
            )
        )
        return

    print(f"FAIL autoscout24 ({status}): {count} listings", file=sys.stderr)
    if payload.get("error"):
        print(f"  error: {payload['error']}", file=sys.stderr)
    if payload.get("hint"):
        print(f"  hint: {payload['hint']}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke live de AutoScout24 DE (fuente principal)."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SEARCH_URL,
        help="URL de listados a comprobar (por defecto, la del canary).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout HTTP en segundos (default: 30).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Salida en JSON (para ops/scripts).",
    )
    args = parser.parse_args()

    exit_code, payload = asyncio.run(_run_smoke(args.url, args.timeout))

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload, exit_code)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
