# Regenera requirements.txt (runtime) y requirements-dev.txt (dev) desde pyproject.toml / uv.lock.
# Fuente de verdad: pyproject.toml (+ uv.lock). NO editar requirements.txt a mano.
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts/export_requirements.ps1
# Requiere uv en PATH (ver Dockerfile: ghcr.io/astral-sh/uv).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Set-Location $root

# Runtime (prod / docker pip install). Pins exactos (==) desde uv.lock.
uv export --no-hashes --no-dev --no-emit-project -o requirements.txt

# Dev pins (incluye runtime + dev group).
uv export --no-hashes --group dev --no-emit-project -o requirements-dev.txt

# Cabecera anti-regresión (se re-antepone porque uv export no la conserva).
$header = @(
    "# GENERATED FILE - do not edit by hand.",
    "# Source of truth: pyproject.toml (+ uv.lock)",
    "# Regenerate: uv export --no-hashes --no-dev --no-emit-project -o requirements.txt",
    "#           (o ejecuta scripts/export_requirements.ps1)",
    ""
) -join "`n"

foreach ($f in @("requirements.txt", "requirements-dev.txt")) {
    $content = Get-Content -Raw -Encoding UTF8 $f
    # Quita cualquier cabecera previa para no duplicarla.
    $body = ($content -split "`n") |
        Where-Object { $_ -notmatch "^# (GENERATED|Source of truth|Regenerate)" }
    $new = $header + "`n" + (($body -join "`n").TrimStart("`r`n"))
    # Escribe UTF-8 SIN BOM (normal para CI/Linux).
    [System.IO.File]::WriteAllText((Join-Path $root $f), $new, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Regenerado: $f"
}

Write-Host "OK - requirements.txt listo (UTF-8 sin BOM)."

# Guardrail Task C.1: fallar si requirements.txt no queda en sync con uv export.
python scripts/check_requirements_sync.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
