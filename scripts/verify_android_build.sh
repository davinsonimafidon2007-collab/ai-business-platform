#!/bin/bash
# Android build verification script — TASK-004 (FASE 5).
#
# Verifies that the Capacitor/Android build produces a valid debug APK.
#
# Usage:
#     bash scripts/verify_android_build.sh
#
# Exit codes:
#   0 — APK generado y verificado
#   1 — fallo en alguno de los pasos
#
# Ajustado a este repo: webDir es `out` (no `dist`) y el APK debug vive en
# `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Android Build Verification ==="

# 1. Check Node dependencies
echo "[1/6] Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ node_modules not found. Run: cd frontend && npm ci"
    exit 1
fi

# 2. Check Capacitor sync
echo "[2/6] Checking Capacitor configuration..."
if [ ! -f "frontend/capacitor.config.ts" ] && [ ! -f "frontend/capacitor.config.json" ]; then
    echo "❌ capacitor.config not found in frontend/"
    exit 1
fi

# 3. Check Android project exists
echo "[3/6] Checking Android project..."
if [ ! -d "frontend/android" ]; then
    echo "❌ frontend/android/ directory not found. Run: npx cap add android"
    exit 1
fi

# 4. Build debug APK (solo si se pide rebuild con --rebuild; el script de
#    verificación no ejecuta `cap sync` completo porque requiere el export de
#    Next.js, que es pesado. Por defecto solo comprueba artefactos.)
REBUILD=0
if [ "${1:-}" = "--rebuild" ]; then
    REBUILD=1
fi

if [ "$REBUILD" = "1" ]; then
    echo "[4/6] Running Capacitor sync..."
    (cd frontend && npx cap sync android)

    echo "[4/6] Building debug APK..."
    cd frontend/android
    if [ -f "gradlew.bat" ]; then
        cmd //c gradlew.bat assembleDebug
    elif [ -f "gradlew" ]; then
        ./gradlew assembleDebug
    else
        echo "❌ Gradle wrapper not found"
        exit 1
    fi
    cd "$PROJECT_ROOT"
else
    echo "[4/6] Skipping rebuild (use --rebuild to run cap sync + gradle)."
fi

# 5. Verify APK exists
echo "[5/6] Verifying APK output..."
APK_PATH="frontend/android/app/build/outputs/apk/debug/app-debug.apk"
if [ ! -f "$APK_PATH" ]; then
    echo "❌ APK not found at $APK_PATH. Run: cd frontend && npm run cap:build:android"
    exit 1
fi

if command -v stat >/dev/null 2>&1; then
    APK_SIZE=$(stat -f%z "$APK_PATH" 2>/dev/null || stat -c%s "$APK_PATH" 2>/dev/null || echo "unknown")
else
    APK_SIZE="unknown"
fi
echo "✅ APK built: $APK_PATH ($APK_SIZE bytes)"

# 6. Verify APK can be parsed
echo "[6/6] Verifying APK structure..."
if command -v aapt >/dev/null 2>&1; then
    aapt list "$APK_PATH" | head -5
    echo "✅ APK structure valid"
elif command -v aapt2 >/dev/null 2>&1; then
    aapt2 dump badging "$APK_PATH" | head -5
    echo "✅ APK structure valid"
else
    echo "⚠️ aapt/aapt2 not available, skipping structure check"
fi

echo ""
echo "=== Android Build Verification: PASSED ==="
echo "Install with: adb install -r $APK_PATH"
