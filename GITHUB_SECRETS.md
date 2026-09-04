# GitHub Secrets & Variables

Este repo usa dos workflows que necesitan secrets/variables distintos:
`.github/workflows/mobile-release-cicd.yml` (release de Android) y
`.github/workflows/deploy.yml` (despliegue del backend a un VPS — ver
`docs/deployment.md` §3-bis). Añádelos en:
`GitHub → tu repo → Settings → Secrets and variables → Actions`.

## 1. Release móvil (MOB-P3-001)

### Secrets (Settings → Secrets and variables → Actions → New repository secret)

| Secret | Requerido para | Descripción |
|--------|----------------|-------------|
| `KEYSTORE_BASE64` | release-aab, firebase-dist | Keystore de firma en **base64**. Genera con `base64 -w0 release.keystore` |
| `KEYSTORE_PASSWORD` | release-aab, firebase-dist | Contraseña del keystore. |
| `KEY_ALIAS` | release-aab, firebase-dist | Alias de la clave de firma. |
| `KEY_PASSWORD` | release-aab, firebase-dist | Contraseña de la clave. |
| `API_URL` | release-aab | URL pública del backend de producción (HTTPS). |
| `FIREBASE_APP_ID` | firebase-dist | ID de la app Android en Firebase App Distribution. |
| `FIREBASE_CREDENTIALS_JSON` | firebase-dist | JSON completo de la service account Firebase (un solo valor). |

### Variables (Settings → Variables → New repository variable)

| Variable | Requerido para | Descripción |
|----------|----------------|-------------|
| `API_URL` | debug-apk | URL del backend para builds de debug (por defecto `http://10.0.2.2:8000`). |

### Cómo crear el keystore (una sola vez)

Usa `scripts/generate-release-keystore.sh` (no `keytool` a mano — el
script exige contraseñas explícitas y evita el default inseguro
`changeit` de `keytool`; ver el propio script para detalles):

```bash
export KEYSTORE_PASSWORD="$(openssl rand -base64 24)"
export KEY_PASSWORD="$KEYSTORE_PASSWORD"   # PKCS12 exige la misma en ambas
bash scripts/generate-release-keystore.sh frontend/android/release-key.jks prod-release 10000
```

El script deja el base64 listo en un archivo `*.base64.txt` (bórralo tras
copiarlo al secret `KEYSTORE_BASE64`) — nunca lo imprime por stdout.

### Verificación rápida del workflow

- **Debug APK**: se ejecuta en cada PR a `main`. El artefacto `app-debug.apk`
  aparece en `Actions → debug-apk → Upload debug APK`.
- **Release AAB**: se ejecuta al crear un tag `v*` (ej. `v1.0.0`). Produce
  `app-release.aab` y una GitHub Release.
- **Firebase Distribution**: sólo con `workflow_dispatch` (botón *Run
  workflow* en la pestaña Actions).

---

## 2. Despliegue del backend (`deploy.yml`)

Un único entorno `production` (VPS personal — ver `docs/deployment.md`
§3-bis, no requiere staging). Configúralo en
`Settings → Environments → production` (o como secrets/variables del
repo si no usas Environments).

### Secrets

| Secret | Descripción |
|--------|-------------|
| `PRODUCTION_HOST` | IP o dominio del VPS, para SSH. |
| `PRODUCTION_USER` | Usuario SSH con Docker instalado y acceso a `/opt/ai-business-platform`. |
| `PRODUCTION_KEY` | Clave privada SSH (la pública ya debe estar en `~/.ssh/authorized_keys` del VPS). |

### Variables

| Variable | Descripción |
|----------|-------------|
| `DOMAIN` | Dominio real del despliegue (ej. `midominio.com`), usado solo para la validación post-despliegue — el valor real que usa Caddy en el servidor vive en `.env.personal` (`DOMAIN`/`ACME_EMAIL`), no aquí. |

### Lo que NO va en GitHub Secrets

`JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
`BACKUP_ENCRYPTION_PASSPHRASE`, `ACME_EMAIL` — todo eso vive únicamente en
`.env.personal` **en el propio VPS**, nunca en GitHub. El workflow solo
hace `git checkout` + `docker compose up` sobre lo que ya está en el
servidor; no necesita conocer esos valores.