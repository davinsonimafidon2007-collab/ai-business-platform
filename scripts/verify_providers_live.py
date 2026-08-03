"""Live smoke for mobile.de / AutoScout24 providers.

Usage:
  uv run python scripts/verify_providers_live.py
  uv run python scripts/verify_providers_live.py --save-html /tmp/provider_html

Exit codes:
  0 — both providers returned useful search+detail data
  1 — at least one provider failed or returned empty/unparseable data
  2 — unexpected setup error
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so `app` is importable regardless of
# how the script is invoked (python scripts/... vs uv run vs -m).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.exceptions import (
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.providers.http_client import ProviderHttpClient
from app.providers.mobile_de import MobileDeProvider

# Full search URLs — VehicleProvider.search() downloads the URL as-is.
MOBILE_DE_SEARCH_URL = (
    "https://suchen.mobile.de/fahrzeuge/search.html"
    "?dam=0&isSearchRequest=true&ms=3500%3B%3B%3B&ref=srp&sb=rel&vc=Car"
    # ms=3500 → BMW; leave model empty for broader results
)
AUTOSCOUT24_SEARCH_URL = (
    "https://www.autoscout24.de/lst/bmw"
    "?atype=C&cy=D&desc=0&sort=standard&source=listpage_search-mask&ustate=N%2CU"
)


def _build_client(provider_name: str, base_url: str) -> ProviderHttpClient:
    """Build HTTP client compatible with post-A.2 ProviderHttpClient.

    The A.2 ProviderHttpClient reads proxy/cookies/delay from settings
    internally when those kwargs are None, so passing the basic kwargs is
    enough. Extra optional kwargs are passed only if present on settings
    (safe for older signatures via TypeError fallback).
    """
    kwargs: dict = {
        "provider_name": provider_name,
        "base_url": base_url,
        "timeout": getattr(settings, "provider_http_timeout", 30.0),
        "max_retries": getattr(settings, "provider_http_max_retries", 3),
    }
    # Optional A.2 fields — ignored if __init__ does not accept them
    optional = {
        "proxy": getattr(settings, "provider_http_proxy", "") or None,
        "cookies": getattr(settings, "provider_http_cookies", "") or None,
        "min_delay_ms": getattr(settings, "provider_http_min_delay_ms", 0),
    }
    try:
        return ProviderHttpClient(**kwargs, **{k: v for k, v in optional.items() if v})
    except TypeError:
        return ProviderHttpClient(**kwargs)


def _useful(detail_or_result: object) -> bool:
    price = getattr(detail_or_result, "price", None)
    brand = getattr(detail_or_result, "brand", None)
    model = getattr(detail_or_result, "model", None)
    return price is not None or bool(brand and model)


async def _maybe_save(save_dir: Path | None, name: str, kind: str, html: str) -> None:
    if save_dir is None:
        return
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{name}_{kind}.html"
    path.write_text(html, encoding="utf-8", errors="replace")
    print(f"  saved_html: {path}")


async def check_provider(
    name: str,
    provider,
    search_url: str,
    save_dir: Path | None,
) -> bool:
    t0 = time.perf_counter()
    print(f"=== {name} ===")
    try:
        results = await provider.search(search_url)
        ms = int((time.perf_counter() - t0) * 1000)
        count = len(results) if results else 0
        print(f"  search: OK  count={count}  elapsed_ms={ms}")

        if count == 0:
            print(
                "  detail: SKIP (empty search — possible selector drift or anti-bot empty page)"
            )
            # Try to capture raw HTML for A.4
            try:
                client = await provider._get_client()
                resp = await client.get(search_url)
                await _maybe_save(save_dir, name, "search_empty", resp.text)
            except Exception:
                pass
            return False

        first = results[0]
        print(
            f"  first: id={first.external_id!r} brand={first.brand!r} "
            f"model={first.model!r} price={first.price!r} year={first.year!r}"
        )

        # Save raw search HTML for A.4 selector work
        if save_dir is not None:
            try:
                search_html = await provider._download_url(search_url)
                await _maybe_save(save_dir, name, "search", search_html)
            except Exception as exc:
                print(f"  warn: could not save search html: {exc}")

        # Prefer the canonical listing URL (result.url) when available so the
        # detail request opens the real annonce page instead of a synthetic
        # /angebote/{external_id} path that may not resolve.
        detail_key = first.url if getattr(first, "url", None) else str(first.external_id)
        t1 = time.perf_counter()
        detail = await provider.get_vehicle(str(detail_key))
        ms_d = int((time.perf_counter() - t1) * 1000)
        print(
            f"  detail: OK  elapsed_ms={ms_d} brand={detail.brand!r} "
            f"model={detail.model!r} price={detail.price!r} year={detail.year!r}"
        )

        # Save raw detail HTML for A.4 selector work
        if save_dir is not None and getattr(detail, "url", None):
            try:
                detail_html = await provider._download_url(str(detail.url))
                await _maybe_save(save_dir, name, "detail", detail_html)
            except Exception as exc:
                print(f"  warn: could not save detail html: {exc}")

        ok = _useful(detail) or _useful(first)
        if not ok:
            print("  warn: no price/brand+model parsed")
        return ok

    except ProviderConnectionError as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"  FAIL  ProviderConnectionError (often HTTP 403 anti-bot)  elapsed_ms={ms}")
        print(f"  detail: {exc}")
        return False
    except ProviderRateLimitError as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"  FAIL  ProviderRateLimitError (HTTP 429)  elapsed_ms={ms}")
        print(f"  detail: {exc}")
        return False
    except ProviderTimeoutError as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"  FAIL  ProviderTimeoutError  elapsed_ms={ms}")
        print(f"  detail: {exc}")
        return False
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"  FAIL  {type(exc).__name__}: {exc}  elapsed_ms={ms}")
        return False
    finally:
        try:
            await provider.close()
        except Exception:
            pass


async def main() -> int:
    parser = argparse.ArgumentParser(description="Live provider verification")
    parser.add_argument("--save-html", type=Path, default=None)
    parser.add_argument(
        "--mobile-url",
        default=MOBILE_DE_SEARCH_URL,
        help="Override mobile.de search URL",
    )
    parser.add_argument(
        "--as24-url",
        default=AUTOSCOUT24_SEARCH_URL,
        help="Override AutoScout24 search URL",
    )
    args = parser.parse_args()

    proxy = getattr(settings, "provider_http_proxy", "") or ""
    delay = getattr(settings, "provider_http_min_delay_ms", 0)
    print(f"config: proxy={'set' if proxy else 'none'}  min_delay_ms={delay}")

    mobile_client = _build_client("mobile_de", "https://suchen.mobile.de")
    as24_client = _build_client("autoscout24", "https://www.autoscout24.de")

    mobile = MobileDeProvider(http_client=mobile_client, base_url="https://suchen.mobile.de")
    as24 = AutoScout24Provider(http_client=as24_client, base_url="https://www.autoscout24.de")

    ok_m = await check_provider("mobile_de", mobile, args.mobile_url, args.save_html)
    ok_a = await check_provider("autoscout24", as24, args.as24_url, args.save_html)

    print("---")
    print(f"RESULT mobile_de={ok_m} autoscout24={ok_a}")
    return 0 if (ok_m and ok_a) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(2) from None