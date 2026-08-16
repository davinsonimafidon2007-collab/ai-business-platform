import os
import subprocess
import sys


def _run_check(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    base = {**os.environ, "ENVIRONMENT": "test"}
    if env:
        base.update(env)
    # Limpiar credenciales opcionales para forzar BLOCKED/SKIP controlados
    for key in (
        "DATABASE_URL",
        "REDIS_URL",
        "SMTP_HOST",
        "JOB_FAILURE_ALERT_TO_EMAIL",
        "FIREBASE_CREDENTIALS_JSON",
        "FIREBASE_CREDENTIALS_PATH",
        "PROVIDER_HTTP_PROXY",
        "ENABLE_AUTOSCOUT24_ES",
    ):
        base.pop(key, None)
    return subprocess.run(
        [sys.executable, "scripts/check_integrations_ready.py", *args],
        capture_output=True,
        text=True,
        env=base,
    )


def test_check_integrations_default_exit_0():
    r = _run_check()
    assert r.returncode == 0, r.stderr
    assert "jwt" in r.stdout
    assert "es_fixtures" in r.stdout
    assert "=== Integrations readiness ===" in r.stdout


def test_check_integrations_blocked_without_credentials():
    r = _run_check()
    assert r.returncode == 0, r.stderr
    assert "BLOCKED" in r.stdout
    assert "smtp" in r.stdout
    assert "firebase" in r.stdout
    assert "mobile_de_proxy" in r.stdout


def test_check_integrations_skip_as24_when_disabled():
    r = _run_check()
    assert r.returncode == 0, r.stderr
    assert "autoscout24_es" in r.stdout
    assert "SKIP" in r.stdout
