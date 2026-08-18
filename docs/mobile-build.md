# Build móvil Android (Capacitor) — Bloque 4

Guía para compilar el APK de **AI Business Platform** para Android desde el
frontend (Next.js + Capacitor 6).

## Requisitos

- Node.js ≥ 18 y npm.
- JDK 17 (Temurin recomendado: https://adoptium.net).
- Android SDK con `cmdline-tools;latest`, `platform-tools`, `build-tools;34.0.0`
  y `platforms;android-34`. Desde Android Studio:
  *Settings > Languages & Frameworks > Android SDK*.
- Variables de entorno (ver `frontend/.env.example`):
  - `NEXT_PUBLIC_API_URL` (obligatoria).
  - `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID` y
    `NEXT_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` (si `NEXT_PUBLIC_AUTH_DISABLED=false`).
  - Credenciales Firebase (Google Login / FCM), **sin valores hardcodeados**:
    el guard `frontend/scripts/check-capacitor-config.mjs` aborta el build si
    detecta credenciales o Client IDs en el código.

> Windows: `ANDROID_HOME` usa `%LOCALAPPDATA%\Android\Sdk` por defecto.
> macOS/Linux: `$HOME/Android/Sdk`.

## Scripts

| Script | Uso | Qué hace |
| --- | --- | --- |
| `frontend/sdk-install.bat` | Windows | Acepta licencias e instala componentes SDK |
| `frontend/full-build.bat` | Windows | Pre-flight + Next build + `cap sync` + APK |
| `frontend/build-android.sh` | macOS/Linux/CI | Equivalente a full-build.bat |

Los tres scripts usan la ruta de su propio directorio (`%~dp0` / `$(dirname ...)`)
y detectan `ANDROID_HOME`, por lo que funcionan desde cualquier checkout.

## Build manual paso a paso

```bash
cd frontend

# 1. Pre-flight (valida config y ausencia de secretos)
node scripts/check-capacitor-config.mjs
npx cap doctor

# 2. Construye la web (Next.js)
npm run build

# 3. Sincroniza assets y plugins a Android
npx cap sync android

# 4. Compila el APK de debug
cd android
./gradlew assembleDebug   # Windows: gradlew.bat assembleDebug
```

Resultado: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.

## Release (firma)

- El keystore de release **no se commitea** (SEC-001). Está en `.gitignore`
  (`android/app/*.keystore`, `android/app/keystore.properties`).
- Para un APK firmado: crea el keystore, define
  `android/app/keystore.properties` y ejecuta:
  ```bash
  cd frontend/android
  ./gradlew assembleRelease
  ```
- FCM y push **no funcionan en debug** (Firebase requiere `google-services.json`
  + `SHA-1` de la firma registrado en Firebase Console). Ver
  `docs/firebase_setup.md`.

## Deep links (App Links)

- Config en `frontend/capacitor.config.ts` → `server.allowNavigation` y el
  intent-filter en `AndroidManifest.xml`.
- El `assetlinks.json` de producción está en `frontend/public/.well-known/`
  con placeholders; sustituye `REPLACE_WITH_*` por el fingerprint SHA-256 real
  de la firma antes de publicar (MOB-P1-009).

## Validación

- `npm run typecheck` (tsc --noEmit) debe pasar.
- `npm test` (vitest) debe pasar.
- `node scripts/check-capacitor-config.mjs` debe salir 0.
- En emulador: la API local se alcanza vía `http://10.0.2.2:8001`
  (host virtualizado de Android). El `network_security_config.xml` permite
  cleartext solo para `10.0.2.2` y `localhost` (desarrollo).
