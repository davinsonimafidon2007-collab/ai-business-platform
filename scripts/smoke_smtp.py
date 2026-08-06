"""Smoke de envío SMTP real (Task SMTP.1).

Envía un email de prueba a través de ``SmtpEmailProvider`` reutilizando las
settings del entorno (``SMTP_*`` en ``.env``). No hardcodea contraseñas: lee
todo de ``app.core.config.settings``.

Uso:
  python scripts/smoke_smtp.py
  python scripts/smoke_smtp.py --to ops@example.com
  python scripts/smoke_smtp.py --job-failure       # + smoke J.1 (requiere SMOKE_SMTP=1)

Comportamiento:
  - Lee settings SMTP del entorno.
  - Si falta host o user -> exit 2 + mensaje "configure SMTP_*".
  - Envía 1 email de prueba subject "[AI Business] SMTP smoke".
  - Exit 0 si el provider no lanza; exit 1 si error de envío (p.ej. credencial
    inválida, host inalcanzable, TLS falla).

Exit codes:
  0 -- email enviado (o job-failure dry-run sin error)
  1 -- error de envío / sin confirmación de SMTP
  2 -- setup: SMTP no configurado o uso inválido
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so `app` is importable regardless of how
# the script is invoked (python scripts/... vs uv run vs -m).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.notifications.email_provider import SmtpEmailProvider

SMOKE_SUBJECT = "[AI Business] SMTP smoke"


def die(code: int, msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke de envío SMTP real (Task SMTP.1)"
    )
    parser.add_argument(
        "--to",
        default="",
        help="Destinatario del email de prueba (default: SMTP_USER / SMTP_FROM_EMAIL).",
    )
    parser.add_argument(
        "--job-failure",
        action="store_true",
        help="Además, invoca JobFailureAlertService.maybe_notify con sender real "
        "solo si SMOKE_SMTP=1 (FIX 3, casi-E2E de J.1).",
    )
    return parser.parse_args()


def check_smtp_configured() -> None:
    """Exit 2 si no hay SMTP configurado (host o user vacíos)."""
    missing = []
    if not settings.smtp_host:
        missing.append("SMTP_HOST")
    if not settings.smtp_user:
        # Sin user no hay autenticación; algunos relay abiertos no lo exigen,
        # pero el spec SMTP.1 exige host+user para el smoke real.
        missing.append("SMTP_USER")
    if missing:
        die(
            2,
            "SMTP no configurado: configure SMTP_* en .env "
            f"(faltan: {', '.join(missing)})",
        )


def default_recipient() -> str:
    """Destinatario por defecto: la propia cuenta SMTP o el from."""
    return settings.smtp_user or settings.smtp_from_email or "noreply@example.com"


async def send_smoke_email(to: str) -> None:
    """Envía un único email de prueba con el provider real."""
    provider = SmtpEmailProvider()
    body_text = (
        "Este es un email de prueba de SMTP (Task SMTP.1).\n"
        "Si lo estás leyendo, el envío SMTP está funcionando.\n"
    )
    body_html = (
        "<p>Este es un <b>email de prueba</b> de SMTP (Task SMTP.1).</p>"
        "<p>Si lo estás leyendo, el envío SMTP está funcionando.</p>"
    )
    await provider.send_email(
        to_email=to,
        subject=SMOKE_SUBJECT,
        body_html=body_html,
        body_text=body_text,
    )


async def smoke_job_failure(to: str) -> None:
    """Smoke casi-E2E de JobFailureAlertService (J.1) con sender real.

    Solo envía por SMTP si ``SMOKE_SMTP=1`` (FIX 3). Si no está activada la
    variable, se informa y no se fuerza el envío real.
    """
    if os.environ.get("SMOKE_SMTP") != "1":
        print("SKIP: job-failure smoke requiere SMOKE_SMTP=1 (sender real). 0")
        return

    from app.services.job_failure_alert_service import JobFailureAlertService

    provider = SmtpEmailProvider()
    svc = JobFailureAlertService(
        email_sender=provider,
        enabled=True,
        threshold=1,
        cooldown_hours=0,
        to_email=to,
    )
    ok = await svc.maybe_notify(
        job_name="smoke-smtp-job-failure",
        consecutive_failures=1,
        failure_count=1,
        last_message="smoke SMTP.1 (probar alerta J.1)",
    )
    if not ok:
        die(1, "job-failure smoke no notificó (maybe_notify devolvió False)")
    print("OK: JobFailureAlertService maybe_notify envió alerta J.1.")


async def amain() -> int:
    args = parse_args()
    check_smtp_configured()

    to = args.to or default_recipient()
    print(f"SMTP smoke → {settings.smtp_host}:{settings.smtp_port}  to={to}")
    print(f"TLS={settings.smtp_use_tls}  from={settings.smtp_from_email}")

    try:
        await send_smoke_email(to)
    except Exception as exc:  # noqa: BLE001 - reporta cualquier fallo de SMTP
        die(1, f"error de envío SMTP: {exc}")

    print(f"OK: email de prueba enviado a {to} (subject='{SMOKE_SUBJECT}').")

    if args.job_failure:
        await smoke_job_failure(to)

    return 0


def main() -> None:
    try:
        code = asyncio.run(amain())
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
