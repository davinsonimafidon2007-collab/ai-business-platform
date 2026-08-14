# GitHub Secrets & Variables para el CI/CD móvil (MOB-P3-001)

Para que el workflow `.github/workflows/mobile-release-cicd.yml` funcione,
añade estos **Secrets** y **Variables** en:
`GitHub → tu repo → Settings → Secrets and variables → Actions`.

## Secrets (Settings → Secrets and variables → Actions → New repository secret)

| Secret | Requerido para | Descripción |
|--------|----------------|-------------|
| `KEYSTORE_BASE64` | release-aab, firebase-dist | Keystore de firma en **base64**. Genera con `base64 -w0 release.keystore` |
| `KEYSTORE_PASSWORD` | release-aab, firebase-dist | Contraseña del keystore. |
| `KEY_ALIAS` | release-aab, firebase-dist | Alias de la clave de firma. |
| `KEY_PASSWORD` | release-aab, firebase-dist | Contraseña de la clave. |
| `API_URL` | release-aab | URL pública del backend de producción (HTTPS). |
| `FIREBASE_APP_ID` | firebase-dist | ID de la app Android en Firebase App Distribution. |
| `FIREBASE_CREDENTIALS_JSON` | firebase-dist | JSON completo de la service account Firebase (un solo valor). |

## Variables (Settings → Variables → New repository variable)

| Variable | Requerido para | Descripción |
|----------|----------------|-------------|
| `API_URL` | debug-apk | URL del backend para builds de debug (por defecto `http://10.0.2.2:8000`). |

## Cómo crear el keystore (una sola vez)

```bash
# En la raíz del repo (o en frontend/android)
keytool -genkey -v -keystore release.keystore \
  -alias my-release-key \
  -keyalg RSA -keysize 2048 -validity 10000
```

Luego exportarlo a base64 para el secret:

```bash
base64 -w0 release.keystore   # Linux / GitHub Actions
# o en Windows (PowerShell):
# [Convert]::ToBase64String([IO.File]::ReadAllBytes("release.keystore"))
```

## Verificación rápida del workflow

- **Debug APK**: se ejecuta en cada PR a `main`. El artefacto `app-debug.apk`
  aparece en `Actions → debug-apk → Upload debug APK`.
- **Release AAB**: se ejecuta al crear un tag `v*` (ej. `v1.0.0`). Produce
  `app-release.aab` y una GitHub Release.
- **Firebase Distribution**: sólo con `workflow_dispatch` (botón *Run
  workflow* en la pestaña Actions).