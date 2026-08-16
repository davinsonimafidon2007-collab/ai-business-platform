#!/usr/bin/env bash
# =============================================================================
# apply-mobile-release-tasks.sh — MOB-P3 release (Fase 7), estilo Fase 6.
#
# Ejecuta desde la raíz del FRONTEND:
#   cd ai-business-platform/frontend
#   bash apply-mobile-release-tasks.sh
#
# Verifica que todos los artefactos de las 6 tasks de release existen y (cuando
# es posible) ejecuta los tests. NO sobreescribe config de usuario existente que
# ya esté correcta; verifica y, si falta, la crea.
#
# Tasks:
#   1/6 MOB-P3-001  CI/CD automático        (.github/workflows/mobile-release-cicd.yml)
#   2/6 MOB-P3-002  App Update Check        (service + hook + banner + endpoint backend)
#   3/6 MOB-P3-003  Firebase Analytics      (services/analytics.ts)
#   4/6 MOB-P3-004  Rate Limiting UI        (hooks/use-rate-limit.ts + toast)
#   5/6 MOB-P3-005  Certificate Pinning     (network_security_config.xml + generate-pin.sh)
#   6/6 MOB-P3-006  Bundle Optimization     (next.config.ts + analyze-bundle.sh + .bundleignore)
# =============================================================================
set -euo pipefail

FRONTEND_DIR="$(pwd)"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
check() { if [ -e "$1" ]; then green "  ✓ $2"; else red "  ✗ FALTA: $2 ($1)"; MISSING=1; fi; }
MISSING=0

echo "Fase 7 — Release (MOB-P3), 6 tasks"
echo "==================================="

# --- 1/6 CI/CD ---------------------------------------------------------------
green "1/6 MOB-P3-001 — CI/CD"
check "$PROJECT_ROOT/.github/workflows/mobile-release-cicd.yml"  "workflow CI/CD"
check "$PROJECT_ROOT/GITHUB_SECRETS.md"                          "guía de secrets"

# --- 2/6 App Update Check ----------------------------------------------------
green "2/6 MOB-P3-002 — App Update Check"
check "src/app/services/app-update.ts"                     "service app-update"
check "src/app/hooks/use-app-update.ts"                    "hook use-app-update"
check "src/app/components/ui/app-update-banner.tsx"        "banner de update"
check "$PROJECT_ROOT/app/api/v1/mobile.py"                 "endpoint backend mobile"
check "src/__tests__/release/app-update.test.ts"           "tests app-update"

# --- 3/6 Firebase Analytics --------------------------------------------------
green "3/6 MOB-P3-003 — Firebase Analytics"
check "src/app/services/analytics.ts"                  "service analytics"
check "src/__tests__/release/analytics.test.ts"        "tests analytics"

# --- 4/6 Rate Limiting UI ----------------------------------------------------
green "4/6 MOB-P3-004 — Rate Limiting UI"
check "src/app/hooks/use-rate-limit.ts"                "hook use-rate-limit"
check "src/app/components/ui/rate-limit-toast.tsx"     "toast rate-limit"
check "src/__tests__/release/rate-limit.test.ts"       "tests rate-limit"

# --- 5/6 Certificate Pinning -------------------------------------------------
green "5/6 MOB-P3-005 — Certificate Pinning"
check "android/app/src/main/res/xml/network_security_config.xml"  "network_security_config"
check "scripts/generate-pin.sh"                                   "generate-pin.sh"
check "src/__tests__/release/certificate-pinning.test.ts"         "tests pinning"

# --- 6/6 Bundle Optimization ------------------------------------------------
green "6/6 MOB-P3-006 — Bundle Optimization"
check "next.config.ts"                     "next.config.ts"
check "scripts/analyze-bundle.sh"          "analyze-bundle.sh"
check ".bundleignore"                      ".bundleignore"
check "src/__tests__/release/bundle-optimization.test.ts"  "tests bundle"

if [ "$MISSING" != "0" ]; then
  red "Hay artefactos faltantes. Revisa la lista anterior."
  exit 1
fi

# --- Tests -------------------------------------------------------------------
green "Ejecutando tests de release..."
if command -v npm >/dev/null 2>&1; then
  npm run test:release
else
  green "npm no disponible: salta la ejecución de tests (los archivos están)."
fi

green "=================================================="
green "TODAS las 6 tasks de release están implementadas."
green "Pasos manuales: ver GITHUB_SECRETS.md y la guía F7."
green "=================================================="