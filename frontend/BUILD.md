# Mobile App Build Guide (MOB-P0-003)

## Requisitos

- **Node.js** ≥ 20.x
- **npm** ≥ 10.x
- **JDK** 17+ (para Gradle)
- **Android SDK** (API 34) via Android Studio o cmdline-tools
- **ANDROID_HOME** o **ANDROID_SDK_ROOT** configurado

## Build Debug (APK)

```bash
cd frontend

# Opción 1: Script automatizado
build-android.bat

# Opción 2: Pasos manuales
npm install
npm run cap:sync:android
cd android
./gradlew assembleDebug
```

El APK se genera en: `android/app/build/outputs/apk/debug/app-debug.apk`

## Build Release (AAB)

### 1. Generar keystore (una vez)

```bash
keytool -genkey -v \
  -keystore release-key.jks \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -alias aibusiness
```

### 2. Configurar variables de entorno

```bash
set KEYSTORE_FILE=path\to\release-key.jks
set KEYSTORE_PASSWORD=tu_password
set KEY_ALIAS=aibusiness
set KEY_PASSWORD=tu_password
```

### 3. Build

```bash
cd android
./gradlew bundleRelease
```

El AAB se genera en: `android/app/build/outputs/bundle/release/app-release.aab`

## Variables de entorno del frontend

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | URL del backend (override para build) |
| `NEXT_PUBLIC_AUTH_DISABLED` | No | `"true"` para modo personal sin login |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Para Google Login | Firebase Web API Key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Para Google Login | Firebase Auth Domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Para Google Login | Firebase Project ID |
| `GOOGLE_WEB_CLIENT_ID` | Para Google Login nativo | Google OAuth Web Client ID |
| `GOOGLE_ANDROID_CLIENT_ID` | Para Google Login nativo | Google OAuth Android Client ID |

## Verificación post-build

1. `npm run typecheck` — debe pasar sin errores
2. `npm run lint` — debe pasar sin errores
3. `npm test` — 110+ tests deben pasar
4. APK se instala en emulador o dispositivo real
5. App abre sin crashes (splash → home)
6. `Settings > Probar conexión` muestra estado OK
