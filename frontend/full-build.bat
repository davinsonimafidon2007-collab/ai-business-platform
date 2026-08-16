@echo off
setlocal enabledelayedexpansion

REM Set environment variables
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
set ANDROID_SDK_ROOT=%LOCALAPPDATA%\Android\Sdk
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot
set PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\build-tools\34.0.0;%PATH%

cd /d "c:\Users\davin\Documents\agentes de ia\frontend"

echo === STEP 1: Accept SDK licenses ===
echo y | sdkmanager --licenses > sdk-licenses.log 2>&1
echo y | sdkmanager --licenses > sdk-licenses.log 2>&1

echo === STEP 2: Install SDK components ===
sdkmanager "build-tools;34.0.0" "platforms;android-34" "platform-tools" > sdk-install.log 2>&1

echo === STEP 3: Build Next.js ===
call npm run build > build.log 2>&1

echo === STEP 4: Capacitor copy ===
call npx cap copy android > cap-copy.log 2>&1

echo === STEP 5: Capacitor sync ===
call npx cap sync android > cap-sync.log 2>&1

echo === STEP 6: Build APK ===
cd android
call gradlew assembleDebug > gradle-build.log 2>&1

echo === DONE ===
if exist "app\build\outputs\apk\debug\app-debug.apk" (
    echo APK FOUND at: %CD%\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo APK NOT FOUND
)

endlocal