#!/usr/bin/env bash
# pre-build-check.sh — Validate Capacitor build prerequisites.
# Run before `npx cap sync` to catch issues early.
#
# Exit codes:
#   0 — all checks passed
#   1 — prerequisite missing

set -euo pipefail

ERRORS=0

echo "=== Capacitor pre-build checks ==="

# 1. Check that `out/` directory exists (webDir for Capacitor)
if [ ! -d "out" ]; then
    echo "ERROR: 'out/' directory not found. Run 'npm run build' first."
    ERRORS=$((ERRORS + 1))
else
    echo "OK: 'out/' directory exists"
fi

# 2. Check that index.html exists in out/
if [ ! -f "out/index.html" ]; then
    echo "ERROR: 'out/index.html' not found. Build may be incomplete."
    ERRORS=$((ERRORS + 1))
else
    echo "OK: 'out/index.html' exists"
fi

# 3. Check capacitor.config.ts exists
if [ ! -f "capacitor.config.ts" ]; then
    echo "ERROR: 'capacitor.config.ts' not found."
    ERRORS=$((ERRORS + 1))
else
    echo "OK: 'capacitor.config.ts' exists"
fi

# 4. Check google-services.json exists (Android)
if [ -d "android" ] && [ ! -f "android/app/google-services.json" ]; then
    echo "WARNING: 'android/app/google-services.json' not found. Android build may fail."
    echo "  Copy from google-services.json.example and fill in your values."
fi

# 5. Check env vars for Google OAuth
if [ -z "${GOOGLE_WEB_CLIENT_ID:-}" ]; then
    echo "WARNING: GOOGLE_WEB_CLIENT_ID not set. Google Auth plugin may not work."
fi

if [ $ERRORS -gt 0 ]; then
    echo "=== FAILED: $ERRORS error(s) found ==="
    exit 1
fi

echo "=== All checks passed ==="
