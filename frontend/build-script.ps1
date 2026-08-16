$ErrorActionPreference = "Continue"

$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:ANDROID_SDK_ROOT = "$env:LOCALAPPDATA\Android\Sdk"
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
$env:PATH = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\cmdline-tools\latest\bin;$env:ANDROID_HOME\build-tools\34.0.0;$env:PATH"

Set-Location "c:\Users\davin\Documents\agentes de ia\frontend"

# Step 1: Accept licenses
Write-Output "=== STEP 1: Accept SDK licenses ==="
"y" | sdkmanager --licenses 2>&1 | Out-File -FilePath "sdk-licenses.log" -Encoding utf8
"y" | sdkmanager --licenses 2>&1 | Out-File -FilePath "sdk-licenses.log" -Encoding utf8 -Append

# Step 2: Install SDK components
Write-Output "=== STEP 2: Install SDK components ==="
sdkmanager "build-tools;34.0.0" "platforms;android-34" "platform-tools" 2>&1 | Out-File -FilePath "sdk-install.log" -Encoding utf8

# Step 3: Build Next.js
Write-Output "=== STEP 3: Build Next.js ==="
npm run build 2>&1 | Out-File -FilePath "build.log" -Encoding utf8

# Step 4: Capacitor copy
Write-Output "=== STEP 4: Capacitor copy ==="
npx cap copy android 2>&1 | Out-File -FilePath "cap-copy.log" -Encoding utf8

# Step 5: Capacitor sync
Write-Output "=== STEP 5: Capacitor sync ==="
npx cap sync android 2>&1 | Out-File -FilePath "cap-sync.log" -Encoding utf8

# Step 6: Build APK
Write-Output "=== STEP 6: Build APK ==="
Set-Location "c:\Users\davin\Documents\agentes de ia\frontend\android"
.\gradlew assembleDebug 2>&1 | Out-File -FilePath "gradle-build.log" -Encoding utf8

# Check result
Write-Output "=== DONE ==="
if (Test-Path "app\build\outputs\apk\debug\app-debug.apk") {
    Write-Output "APK FOUND at: $(Get-Location)\app\build\outputs\apk\debug\app-debug.apk"
} else {
    Write-Output "APK NOT FOUND"
}

Write-Output "ALL STEPS COMPLETE" | Out-File -FilePath "c:\Users\davin\Documents\agentes de ia\frontend\build-complete.txt" -Encoding utf8