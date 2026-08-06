"""Release checklist local (Task REL.1).

  python scripts/release_check.py
  python scripts/release_check.py --with-api --with-opportunities
  python scripts/release_check.py --skip-pytest
  python scripts/release_check.py --skip-smoke --with-integration
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Subconjunto crítico de integration estable bajo ENVIRONMENT=test (Task INT.1).
# No incluye DB/Postgres, providers live ni tests marcados skip.
INTEGRATION_SUBSET = [
    "tests/integration/test_admin_status_api.py",
    "tests/integration/test_api_keys_api.py",
    "tests/integration/test_admin_api_keys_api.py",
    "tests/integration/test_auth_api.py",
    "tests/integration/test_vehicles_api.py",
]


def run(label: str, argv: list[str], *, env: dict | None = None) -> None:
    print(f"\n=== {label} ===")
    print(">", " ".join(argv))
    r = subprocess.run(argv, cwd=ROOT, env=env or os.environ.copy())
    if r.returncode != 0:
        print(f"FAIL: {label} (exit {r.returncode})", file=sys.stderr)
        raise SystemExit(r.returncode)
    print(f"OK: {label}")


def main() -> None:
    p = argparse.ArgumentParser(description="Local release checklist")
    p.add_argument("--skip-pytest", action="store_true")
    p.add_argument("--skip-smoke", action="store_true")
    p.add_argument("--skip-requirements", action="store_true")
    p.add_argument("--with-api", action="store_true", help="Require API up + run smoke")
    p.add_argument("--with-integration", action="store_true",
                   help="Run critical integration subset (INT.1) after unit")
    p.add_argument("--with-opportunities", action="store_true")
    p.add_argument("--with-admin", action="store_true")
    p.add_argument(
        "--pytest-args",
        default="tests/unit -q",
        help='Default: "tests/unit -q"',
    )
    args = p.parse_args()

    # ENV.1 — Python 3.14 no soportado aún (p.ej. lxml sin wheels en Windows).
    current = sys.version_info
    if current >= (3, 14):
        print(
            "\nERROR: Python 3.14 no está soportado todavía por este proyecto.\n"
            "  Algunas dependencias con binarios nativos (p.ej. lxml) no publican\n"
            "  wheels para 3.14 en Windows y fallan al compilar.\n"
            "  Usa Python 3.13.x:\n"
            f"    python -m venv --python 3.13 .venv    # o: uv venv --python 3.13\n"
            f"    .venv\\Scripts\\activate\n"
            f"  (detectado: {current.major}.{current.minor}.{current.micro})",
            file=sys.stderr,
        )
        raise SystemExit(2)

    py = sys.executable

    if not args.skip_requirements:
        run("requirements sync", [py, "scripts/check_requirements_sync.py"])

    if not args.skip_pytest:
        # ENVIRONMENT=test evita JWT_SECRET en muchos tests
        env = os.environ.copy()
        env.setdefault(
            "JWT_SECRET_KEY",
            "test_secret_key_that_is_at_least_32_characters_long_1234567890",
        )
        env.setdefault("ENVIRONMENT", "test")
        run("pytest unit", [py, "-m", "pytest", *args.pytest_args.split()], env=env)

    if args.with_integration:
        # INT.1 — subconjunto crítico de integration (mismo env que unit).
        env = os.environ.copy()
        env.setdefault(
            "JWT_SECRET_KEY",
            "test_secret_key_that_is_at_least_32_characters_long_1234567890",
        )
        env.setdefault("ENVIRONMENT", "test")
        run("pytest integration (INT.1 subset)", [py, "-m", "pytest", "-q", *INTEGRATION_SUBSET], env=env)

    if args.with_api or not args.skip_smoke:
        # Por defecto: intentar smoke; si API down → exit 2 del smoke
        smoke_cmd = [py, "scripts/smoke_critical_path.py"]
        if args.with_opportunities:
            smoke_cmd.append("--with-opportunities")
        if args.with_admin:
            smoke_cmd.append("--with-admin")
        if args.with_api:
            run("smoke critical path", smoke_cmd)
        else:
            # Sin --with-api: smoke opcional — si exit 2 (API down), advertir y no fallar release de solo unit+deps
            print("\n=== smoke (optional unless --with-api) ===")
            r = subprocess.run(smoke_cmd, cwd=ROOT)
            if r.returncode == 0:
                print("OK: smoke")
            elif r.returncode == 2:
                print("SKIP: smoke (API not reachable). Use --with-api to require it.")
            else:
                print(f"FAIL: smoke (exit {r.returncode})", file=sys.stderr)
                raise SystemExit(r.returncode)

    print("\n=== RELEASE CHECK PASSED ===")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
