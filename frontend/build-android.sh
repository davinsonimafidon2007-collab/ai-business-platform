#!/usr/bin/env bash
# Build completo Android (Bloque 4 - MOB-P0) para CI / macOS / Linux.
# Equivalente a full-build.bat (Windows).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

if [[ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]]; then
  echo "ERROR: sdkmanager no encontrado en $ANDROID_HOME/cmdline-tools/latest/bin" >&2
  exit 1
fi

echo "=== STEP 0: Pre-flight checks ==="
npx cap doctor
node scripts/check-capacitor-config.mjs

echo "=== STEP 1: Accept SDK licenses ==="
yes | sdkmanager --licenses > sdk-licenses.log 2>&1 || true

echo "=== STEP 2: Install SDK components ==="
sdkmanager "build-tools;34.0.0" "platforms;android-34" "platform-tools" > sdk-install.log 2>&1

echo "=== STEP 3: Build Next.js ==="
npm run build > build.log 2>&1

echo "=== STEP 4: Capacitor sync ==="
npx cap sync android > cap-sync.log 2>&1

echo "=== STEP 5: Build APK ==="
cd "$ROOT/android"
./gradlew assembleDebug > gradle-build.log 2>&1

echo "=== DONE ==="
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
if [[ -f "$APK" ]]; then
  echo "APK found at: $APK"
else
  echo "APK NOT FOUND" >&2
  exit 1
fi