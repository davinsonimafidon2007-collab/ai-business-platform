#!/usr/bin/env bash
# =============================================================================
# MOB-P3-006 — Análisis de bundle con @next/bundle-analyzer.
#
# Uso:
#   bash scripts/analyze-bundle.sh
#
# Genera el reporte HTML de análisis y lo abre en el navegador por defecto.
# Lanza `next build` con ANALYZE=true; el reporte queda en .next/analyze/.
# =============================================================================
set -euo pipefail

# Solo instalar bundle-analyzer si no está presente (devDependency opcional).
if ! npm ls @next/bundle-analyzer >/dev/null 2>&1; then
  echo "→ Instalando @next/bundle-analyzer (dev) ..."
  npm install -D @next/bundle-analyzer
fi

echo "→ Build con análisis de bundle (ANALYZE=true) ..."
ANALYZE=true npm run build

echo
echo "Reportes generados en: .next/analyze/"
echo "Abre los .html de cada chunk para ver el desglose por módulo."

# Abrir en el navegador por defecto si está en un entorno con GUI.
if command -v python3 >/dev/null 2>&1; then
  python3 -m webbrowser ".next/analyze/client.html" 2>/dev/null || true
fi