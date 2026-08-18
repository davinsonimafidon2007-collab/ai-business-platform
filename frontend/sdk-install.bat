@echo off
REM SDK Installer / Updater (Bloque 4 - MOB-P0).
REM Instala los componentes del Android SDK necesarios para compilar la app.

setlocal

if "%ANDROID_HOME%"=="" set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set ANDROID_SDK_ROOT=%ANDROID_HOME%
set PATH=%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools;%PATH%

if not exist "%ANDROID_HOME%\cmdline-tools\latest\bin\sdkmanager.bat" (
    echo. ERROR: sdkmanager no encontrado en %ANDROID_HOME%\cmdline-tools\latest\bin
    echo.   Instala 'Android SDK Command-line Tools' desde Android Studio:
    echo.   Settings > Languages & Frameworks > Android SDK > SDK Tools
    exit /b 1
)

echo === Accepting SDK licenses ===
call sdkmanager.bat --licenses < NUL > sdk-licenses.log 2>&1

echo === Installing SDK components ===
set COMPONENTS=platforms;android-34 build-tools;34.0.0 platform-tools

echo. Usando ANDROID_HOME: %ANDROID_HOME%
call sdkmanager.bat %COMPONENTS% > sdk-install.log 2>&1

if errorlevel 1 (
    echo. ERROR: sdkmanager fallo. Revisa sdk-install.log
    exit /b 1
)

echo. SDK listo.
endlocal