# scripts/lint.ps1 — Check de higiene (ruff) para CODE-001.
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts/lint.ps1            # ruff check app tests
#   powershell -ExecutionPolicy Bypass -File scripts/lint.ps1 -Format    # + ruff format (solo archivos tocados)
#   powershell -ExecutionPolicy Bypass -File scripts/lint.ps1 -Vulture   # + vulture (opcional, guía)
param(
    [switch]$Format,
    [switch]$Vulture
)

$ErrorActionPreference = "Stop"

Write-Host "==> ruff check app tests" -ForegroundColor Cyan
uv run ruff check app tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "ruff check falló (exit $LASTEXITCODE). Ver errores arriba." -ForegroundColor Red
    exit $LASTEXITCODE
}

if ($Format) {
    Write-Host "==> ruff format --check app tests (modo check)" -ForegroundColor Cyan
    uv run ruff format --check app tests
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Hay archivos sin formatear. Revisa los listados o ejecuta 'uv run ruff format app tests' en un commit separado documentado (CODE-001)." -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

if ($Vulture) {
    Write-Host "==> vulture app --min-confidence 80 (guía, no bloqueante)" -ForegroundColor Cyan
    # vulture es opcional; si no está instalado, muestra aviso y continúa.
    try {
        uv run vulture app --min-confidence 80
    } catch {
        Write-Host "vulture no disponible (opcional). Ignorando." -ForegroundColor Yellow
    }
}

Write-Host "Lint OK (CODE-001)" -ForegroundColor Green
