# Build móvil Android (Capacitor) — Bloque 4

Guía para compilar el APK de **AI Business Platform** para Android desde el
frontend (Next.js + Capacitor 6).

## Requisitos

- Node.js ≥ 18 y npm.
- JDK 17 (Temurin recomendado: https://adoptium.net).
- Android SDK con `cmdline-tools;latest`, `platform-tools`, `build-tools;35.0.0`
  y `platforms;android-36`. Desde Android Studio:
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

## Versionado (fuente única)

- El archivo `VERSION` en la raíz del repo (SemVer: `X.Y.Z`) es la **única
  fuente de versión** (MOB-P1-004):
  - Android: `app/build.gradle` deriva `versionName = X.Y.Z` y
    `versionCode = X*1000000 + Y*1000 + Z`.
  - Backend: `app/api/v1/mobile.py` lo lee como fallback para el endpoint de
    update-check.
  - Web: `next.config.ts` lo inyecta como `NEXT_PUBLIC_APP_VERSION` en build.
- En CI release, la versión se fija desde el tag `vX.Y.Z` (job `release`
  reescribe `VERSION` con `git describe`). No editar `VERSION` a mano antes de
  un release por tag.

## Release (firma)

- El keystore de release **no se commitea**. `.gitignore` cubre
  `frontend/android/keystore/`, `*.jks`, `*.keystore`,
  `frontend/android/keystore.properties` y `frontend/android/app/release.keystore`.
- Firma unificada (MOB-P1-006): `signingConfigs.release` resuelve credenciales
  en este orden:
  1. `frontend/android/keystore.properties` con las claves
     `storeFile`, `storePassword`, `keyAlias`, `keyPassword` (local).
     Rutas relativas se resuelven contra `frontend/android/`.
  2. Variables de entorno `KEYSTORE_FILE`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`,
     `KEY_PASSWORD` (los mismos nombres que usan los secrets de GitHub Actions).
  3. Sin credenciales: el build type `release` firma con la config debug y
     emite un warning — útil para smoke tests, **no** publicar ese AAB.
- Para un AAB firmado local:
  ```bash
  cd frontend/android
  ./gradlew bundleRelease
  ```
- FCM y push **no funcionan en debug** (Firebase requiere `google-services.json`
  + `SHA-1` de la firma registrado en Firebase Console). Ver
  `docs/firebase_setup.md`.

## Deep links (App Links)

- Host productivo único: **`aibusiness.app`** (autoVerify). El filtro
  `https://app.aibusiness.com` y el scheme inexistente `aibusiness.platform`
  fueron eliminados del manifest (MOB-P1-009).
- Config en `frontend/capacitor.config.ts` → `server.allowNavigation:
  ["aibusiness.app"]`.
- El `assetlinks.json` de producción está en `frontend/public/.well-known/`
  con placeholders; sustituye el fingerprint SHA-256 real de la firma antes de
  publicar y verifica `https://aibusiness.app/.well-known/assetlinks.json`.
- Parser (`use-deep-links.ts`): acepta `aibusiness://` y
  `https://aibusiness.app`; soporta búsqueda en path
  (`aibusiness://search/Toyota`) y queryParams; cold start vía
  `App.getLaunchUrl()`. Cubierto por tests en
  `src/__tests__/mobile/deep-links.test.ts`.

## Seguridad de red

- Release: cleartext HTTP **deshabilitado por completo**
  (`network_security_config.xml` de `src/main`, MOB-P1-007).
- Debug: overlay `src/debug/res/xml/network_security_config.xml` permite
  cleartext solo para `10.0.2.2` y `localhost` (emulador/desarrollo).

## CI/CD

- Workflow: `.github/workflows/mobile-release-cicd.yml`
  - `debug-apk`: quality gate (lint, vitest, check-cap-config, export,
    `cap sync`, `assembleDebug`) + artefacto APK en cada push a `main`.
  - `release`: manual (`workflow_dispatch`) o tag `vX.Y.Z`; fija VERSION,
    decodifica secrets `KEYSTORE_*`, valida SemVer y verifica que el AAB no
    esté vacío antes de subirlo a Firebase App Distribution.

## Validación

- `npm run typecheck` (tsc --noEmit) debe pasar.
- `npm run test:run` (vitest) debe pasar.
- `node scripts/check-capacitor-config.mjs` debe salir 0.
- En emulador: la API local se alcanza vía `http://10.0.2.2:8001`
  (host virtualizado de Android). Permitido únicamente por el overlay debug;
  el binario de release rechaza cualquier tráfico cleartext.
