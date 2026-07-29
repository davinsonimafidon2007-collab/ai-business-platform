@echo off
cd /d "%~dp0"
echo === STEP 1: Check Node and npm ===
call node --version
call npm --version
echo.
echo === STEP 2: Install dependencies if needed ===
if not exist "node_modules\.package-lock.json" (
    echo Installing npm dependencies...
    call npm install
)
echo.
echo === STEP 3: Build Next.js static export ===
echo Building Next.js...
call npx next build
if errorlevel 1 (
    echo ERROR: Next.js build failed!
    exit /b 1
)
echo.
echo STEP 4: Check output directory
if exist "out\index.html" (
    echo SUCCESS: out/index.html exists
) else (
    echo WARNING: out/index.html not found
    dir out
)
echo.
echo === STEP 5: Install Capacitor dependencies ===
call npm install @capacitor/core @capacitor/cli @capacitor/android
echo.
echo === STEP 6: Initialize Capacitor if needed ===
if not exist "capacitor.config.ts" (
    call npx cap init --web-dir out "AI Business Platform" com.aibusiness.platform
)
echo.
echo === STEP 7: Copy web build to Capacitor ===
call npx cap copy
echo.
echo === STEP 8: Add Android platform ===
if not exist "android" (
    call npx cap add android
)
echo.
echo === STEP 9: Build APK ===
cd android
call gradlew assembleDebug
cd ..
echo.
echo === BUILD COMPLETE ===
if exist "android\app\build\outputs\apk\debug\app-debug.apk" (
    echo APK GENERATED: android\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo APK NOT FOUND - check build output
)
pause

