#!/usr/bin/env python3
"""Informe READY / BLOCKED / SKIP de integraciones (ops).

Exit 0 por defecto (solo informe).
Exit 1 con --strict si alguna integración marcada required no está READY.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Asegurar importabilidad de `app` desde scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@dataclass
class Row:
    name: str
    status: str  # READY | BLOCKED | SKIP
    detail: str


def _nonempty(val: str | None) -> bool:
    return bool(val and str(val).strip())


def check_jwt() -> Row:
    key = os.getenv("JWT_SECRET_KEY") or ""
    try:
        from app.core.config import settings

        key = key or (settings.jwt_secret_key or "")
    except Exception:  # noqa: BLE001
        pass
    if len(key) >= 32:
        return Row("jwt", "READY", f"len={len(key)}")
    return Row("jwt", "BLOCKED", "JWT_SECRET_KEY missing or < 32 chars")


def check_db() -> Row:
    url = os.getenv("DATABASE_URL", "")
    try:
        from app.core.config import settings

        url = url or getattr(settings, "database_url", "") or ""
    except Exception:  # noqa: BLE001
        pass
    if _nonempty(url):
        # no imprimir password
        safe = url.split("@")[-1] if "@" in url else "(set)"
        return Row("database", "READY", f"host={safe}")
    return Row("database", "BLOCKED", "DATABASE_URL empty")


def check_redis() -> Row:
    url = os.getenv("REDIS_URL", "")
    try:
        from app.core.config import settings

        url = url or getattr(settings, "redis_url", "") or ""
    except Exception:  # noqa: BLE001
        pass
    if not _nonempty(url):
        return Row("redis", "SKIP", "not configured (optional)")
    return Row("redis", "READY", "REDIS_URL set (ping not required here)")


def check_smtp() -> Row:
    try:
        from app.core.config import settings

        host = getattr(settings, "smtp_host", None) or os.getenv("SMTP_HOST", "")
        to_email = getattr(settings, "job_failure_alert_to_email", None) or os.getenv(
            "JOB_FAILURE_ALERT_TO_EMAIL", ""
        )
    except Exception:  # noqa: BLE001
        host = os.getenv("SMTP_HOST", "")
        to_email = os.getenv("JOB_FAILURE_ALERT_TO_EMAIL", "")
    if _nonempty(host) and _nonempty(to_email):
        return Row("smtp", "READY", f"host={host} to=set")
    if not _nonempty(host):
        return Row("smtp", "BLOCKED", "SMTP_HOST empty (app stays log-only)")
    return Row("smtp", "BLOCKED", "JOB_FAILURE_ALERT_TO_EMAIL empty")


def check_firebase() -> Row:
    try:
        from app.core.config import settings

        raw = getattr(settings, "firebase_credentials_json", None) or ""
        path = getattr(settings, "firebase_credentials_path", None) or ""
    except Exception:  # noqa: BLE001
        raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
        path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if _nonempty(raw) and raw.strip() not in ("{}", "null"):
        return Row("firebase", "READY", "FIREBASE_CREDENTIALS_JSON set")
    if _nonempty(path) and Path(path).is_file():
        return Row("firebase", "READY", f"path={path}")
    return Row("firebase", "BLOCKED", "no service account (Google login backend)")


def check_proxy() -> Row:
    try:
        from app.core.config import settings

        proxy = getattr(settings, "provider_http_proxy", None) or os.getenv(
            "PROVIDER_HTTP_PROXY", ""
        )
    except Exception:  # noqa: BLE001
        proxy = os.getenv("PROVIDER_HTTP_PROXY", "")
    if _nonempty(proxy):
        return Row("mobile_de_proxy", "READY", "PROVIDER_HTTP_PROXY set")
    return Row("mobile_de_proxy", "BLOCKED", "no proxy (A.5b / canary mobile.de)")


def check_as24_es() -> Row:
    try:
        from app.core.config import settings

        enabled = bool(getattr(settings, "enable_autoscout24_es", False))
    except Exception:  # noqa: BLE001
        enabled = os.getenv("ENABLE_AUTOSCOUT24_ES", "").lower() in ("1", "true", "yes")
    if enabled:
        return Row("autoscout24_es", "READY", "ENABLE_AUTOSCOUT24_ES=true")
    return Row("autoscout24_es", "SKIP", "flag false (live off)")


def check_es_fixtures() -> Row:
    from app.providers.coches_net_fixture import CochesNetFixtureProvider
    from app.providers.es_market_fixture import EsMarketFixtureProvider

    # sync presence only
    es = EsMarketFixtureProvider()
    cn = CochesNetFixtureProvider()
    n_es = len(es._listings)
    n_cn = len(cn._listings)
    if n_es >= 1 and n_cn >= 1:
        return Row("es_fixtures", "READY", f"es={n_es} coches_net={n_cn}")
    return Row("es_fixtures", "BLOCKED", "fixture JSON empty or missing")


def main() -> int:
    parser = argparse.ArgumentParser(description="Integration readiness report")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if jwt/database/es_fixtures not READY",
    )
    args = parser.parse_args()

    rows = [
        check_jwt(),
        check_db(),
        check_redis(),
        check_smtp(),
        check_firebase(),
        check_proxy(),
        check_as24_es(),
        check_es_fixtures(),
    ]

    width = max(len(r.name) for r in rows)
    print("=== Integrations readiness ===")
    for r in rows:
        print(f"{r.name:<{width}}  {r.status:<7}  {r.detail}")

    blocked = [r for r in rows if r.status == "BLOCKED"]
    print("---")
    print(f"READY={sum(1 for r in rows if r.status == 'READY')}  "
          f"BLOCKED={len(blocked)}  SKIP={sum(1 for r in rows if r.status == 'SKIP')}")

    if args.strict:
        required = {"jwt", "database", "es_fixtures"}
        bad = [r for r in rows if r.name in required and r.status != "READY"]
        if bad:
            print("STRICT fail:", ", ".join(r.name for r in bad), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
