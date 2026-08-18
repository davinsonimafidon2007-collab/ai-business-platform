@echo off
REM Build completo Android (Bloque 4 - MOB-P0).
REM Pre-flight checks + Next build + Capacitor sync + APK.
REM Sustituye a la version vieja que apuntaba a una ruta hardcodeada.

setlocal enabledelayedexpansion

set ROOT=%~dp0
cd /d "%ROOT%"

if "%ANDROID_HOME%"=="" set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set ANDROID_SDK_ROOT=%ANDROID_HOME%
set JAVA_HOME=%ProgramFiles%\Java\jdk-17

if not exist "%JAVA_HOME%\bin\java.exe" (
    echo. ERROR: JDK 17 no encontrado en %JAVA_HOME%
    echo.   Descargalo de https://adoptium.net (Temurin 17)
    exit /b 1
)

set PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\build-tools\34.0.0;%PATH%

echo === STEP 0: Pre-flight checks ===
call npx cap doctor > cap-doctor.log 2>&1
call node scripts/check-capacitor-config.mjs || exit /b 1

echo === STEP 1: Accept SDK licenses ===
call sdkmanager.bat --licenses < NUL > sdk-licenses.log 2>&1

echo === STEP 2: Install SDK components ===
call sdkmanager.bat "build-tools;34.0.0" "platforms;android-34" "platform-tools" > sdk-install.log 2>&1

echo === STEP 3: Build Next.js ===
call npm run build > build.log 2>&1
if errorlevel 1 (
    echo. ERROR: Next build fallo. Revisa build.log
    exit /b 1
)

echo === STEP 4: Capacitor sync ===
call npx cap sync android > cap-sync.log 2>&1
if errorlevel 1 (
    echo. ERROR: Capacitor sync fallo. Revisa cap-sync.log
    exit /b 1
)

echo === STEP 5: Build APK ===
cd /d "%ROOT%android"
call gradlew.bat assembleDebug > gradle-build.log 2>&1
if errorlevel 1 (
    echo. ERROR: Gradle fallo. Revisa gradle-build.log
    exit /b 1
)

echo === DONE ===
set APK=%ROOT%android\app\build\outputs\apk\debug\app-debug.apk
if exist "%APK%" (
    echo APK FOUND at: %APK%
) else (
    echo APK NOT FOUND
)

endlocal