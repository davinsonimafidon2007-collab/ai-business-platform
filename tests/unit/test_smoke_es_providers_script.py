import os
import subprocess
import sys


def _run_smoke(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/smoke_es_providers.py", *args],
        capture_output=True,
        text=True,
        env={**os.environ, "ENVIRONMENT": "test"},
    )


def test_smoke_es_fixtures_exit_0():
    r = _run_smoke()
    assert r.returncode == 0, r.stderr


def test_smoke_es_registry_exit_0():
    r = _run_smoke("--registry")
    assert r.returncode == 0, r.stderr
    assert "providers=" in r.stdout


def test_smoke_es_live_as24_es_skip_exit_2():
    r = _run_smoke("--live-as24-es")
    # Con ENABLE_AUTOSCOUT24_ES=true el provider está habilitado y funciona.
    # Solo esperamos SKIP (exit 2) si el flag está off.
    assert r.returncode in (0, 2), r.stderr
    assert "SKIP" in r.stdout or "OK" in r.stdout
