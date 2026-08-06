"""Smoke Firebase / Google login (Task FIRE.1).

Comprueba que el Admin SDK se inicializa y, opcionalmente, verifica un
ID token real pasado por CLI.

Uso:
  python scripts/smoke_firebase.py
  python scripts/smoke_firebase.py --id-token <FIREBASE_ID_TOKEN>
  python scripts/smoke_firebase.py --id-token <TOKEN> --call-api
      # POST /api/v1/auth/google contra BASE_URL (default http://127.0.0.1:8000)

Comportamiento:
  - Sin FIREBASE_CREDENTIALS_JSON ni FIREBASE_CREDENTIALS_PATH → exit 2
  - Con credenciales: inicializa Admin SDK; si no hay --id-token → exit 0
    con mensaje "Firebase OK (init only)"
  - Con --id-token: verify_google_id_token; imprime email/uid; exit 0/1
  - Con --call-api: además POST al endpoint y espera 200 + tokens

Exit codes:
  0 — init OK (y verify/API OK si se pidieron)
  1 — error de verify / API
  2 — setup: sin credenciales Firebase
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Reset singleton so env from this process is respected
import app.core.firebase as firebase_mod

firebase_mod._firebase_app = None

from app.core.firebase import get_firebase_app, verify_google_id_token


def die(code: int, msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke Firebase / Google (FIRE.1)")
    p.add_argument(
        "--id-token",
        default="",
        help="Firebase ID token real (obtenido del front o Firebase Auth).",
    )
    p.add_argument(
        "--call-api",
        action="store_true",
        help="Además POST /api/v1/auth/google (requiere API up + --id-token).",
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"),
        help="Base URL de la API (default BASE_URL o http://127.0.0.1:8000).",
    )
    return p.parse_args()


def check_firebase_configured() -> None:
    has_json = bool(os.environ.get("FIREBASE_CREDENTIALS_JSON") or "")
    has_path = bool(os.environ.get("FIREBASE_CREDENTIALS_PATH") or "")
    # settings may also expose the fields if loaded from .env
    try:
        from app.core.config import settings

        has_json = has_json or bool(getattr(settings, "firebase_credentials_json", "") or "")
        has_path = has_path or bool(getattr(settings, "firebase_credentials_path", "") or "")
        # Mirror settings into os.environ so get_firebase_app (reads env) sees them
        if getattr(settings, "firebase_credentials_json", "") and not os.environ.get(
            "FIREBASE_CREDENTIALS_JSON"
        ):
            os.environ["FIREBASE_CREDENTIALS_JSON"] = settings.firebase_credentials_json
        if getattr(settings, "firebase_credentials_path", "") and not os.environ.get(
            "FIREBASE_CREDENTIALS_PATH"
        ):
            os.environ["FIREBASE_CREDENTIALS_PATH"] = settings.firebase_credentials_path
    except Exception:
        pass

    if not has_json and not has_path:
        die(
            2,
            "Firebase no configurado: set FIREBASE_CREDENTIALS_JSON o "
            "FIREBASE_CREDENTIALS_PATH en .env (service account JSON).",
        )


def main() -> None:
    args = parse_args()
    check_firebase_configured()

    app = get_firebase_app()
    if app is None:
        die(1, "get_firebase_app() devolvió None (¿JSON inválido o paquete ausente?)")

    print("OK: Firebase Admin SDK initialized")

    if not args.id_token:
        print("Firebase OK (init only). Pasa --id-token para verify.")
        raise SystemExit(0)

    async def _verify() -> dict:
        return await verify_google_id_token(args.id_token)

    try:
        claims = asyncio.run(_verify())
    except ValueError as exc:
        die(1, f"verify_google_id_token: {exc}")
    except Exception as exc:
        die(1, f"verify error: {type(exc).__name__}: {exc}")

    print(
        "OK: token verified "
        f"uid={claims.get('uid')!r} email={claims.get('email')!r} "
        f"verified={claims.get('email_verified')}"
    )

    if args.call_api:
        try:
            import urllib.request

            url = args.base_url.rstrip("/") + "/api/v1/auth/google"
            body = json.dumps({"id_token": args.id_token}).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                if resp.status != 200:
                    die(1, f"API status={resp.status} body={data}")
                if "access_token" not in data:
                    die(1, f"API sin access_token: {data}")
                print(f"OK: POST {url} → 200 access_token present")
        except Exception as exc:
            die(1, f"API call failed: {type(exc).__name__}: {exc}")

    raise SystemExit(0)


if __name__ == "__main__":
    main()
