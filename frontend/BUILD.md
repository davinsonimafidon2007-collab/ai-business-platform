# Mobile App Build Guide (MOB-P0-003)

## Requisitos

- **Node.js** ≥ 20.x
- **npm** ≥ 10.x
- **JDK** 17+ (para Gradle)
- **Android SDK** (API 34) via Android Studio o cmdline-tools
- **ANDROID_HOME** o **ANDROID_SDK_ROOT** configurado

## Variables de entorno del frontend

Crea `frontend/.env.local` (no se commitea) basándote en `.env.example`:

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | URL del backend (override para build) |
| `NEXT_PUBLIC_AUTH_DISABLED` | No | `"true"` para modo personal sin login |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Para Google Login | Firebase Web API Key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Para Google Login | Firebase Auth Domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Para Google Login | Firebase Project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Para Google Login | Firebase Storage Bucket |
| `NEXT_PUBLIC_FIREBASE_SENDER_ID` | Para Google Login | Firebase Sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Para Google Login | Firebase App ID |
| `NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID` | Opcional | Firebase Measurement ID |
| `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID` | Para Google Login nativo | Google OAuth Web Client ID (`client_type 3`) |
| `NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` | Para Google Login nativo | Google OAuth Android Client ID (`client_type 1`) |
| `NEXT_PUBLIC_GOOGLE_IOS_CLIENT_ID` | Opcional | Google OAuth iOS Client ID |

> **Nota:** `scripts/check-capacitor-config.mjs` bloquea el build si faltan las variables requeridas.

## Google Login: configuración de credenciales

### 1. Obtener el SHA-1 del keystore de debug

```bash
# Linux/macOS
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android | grep SHA1

# Windows (PowerShell)
keytool -list -v -keystore "$env:USERPROFILE\.android\debug.keystore" -alias androiddebugkey -storepass android -keypass android | findstr SHA1
```

### 2. Crear client IDs en Google Cloud Console / Firebase Console

1. Abre [Google Cloud Console](https://console.cloud.google.com/apis/credentials) o [Firebase Console](https://console.firebase.google.com).
2. Crea dos OAuth 2.0 Client IDs:
   - **Web application** → copia el Client ID como `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID`.
   - **Android** → usa el package name `com.aibusiness.platform` y el SHA-1 del paso 1 → copia el Client ID como `NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID`.
3. (Opcional) iOS client ID si publicas en App Store.

### 3. google-services.json (solo para Push Notifications)

Si necesitas Push Notifications, descarga `google-services.json` desde Firebase Console y colócalo en:
```
frontend/android/app/google-services.json
```
Este archivo ya está en `.gitignore` (correcto). Sin él, el login Google funciona igual; solo se desactivan las notificaciones push silenciosamente (ver `android/app/build.gradle:70`).

### 4. Pre-flight check

```bash
cd frontend
node scripts/check-capacitor-config.mjs
```

Si falla, completa las variables faltantes en `.env.local` antes de continuar.

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
