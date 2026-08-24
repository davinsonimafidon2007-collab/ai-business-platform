# Seguridad — AI Business Platform

## Visión general

La plataforma sigue las mejores prácticas de seguridad para aplicaciones web y móviles:

- **Autenticación**: Google OAuth con JWT (access + refresh tokens).
- **Autorización**: Middleware `AuthenticationMiddleware` y dependencias de permisos en endpoints protegidos.
- **CORS**: Restringido a dominios configurados en producción (`CORS_ORIGINS`).
- **HTTPS**: Redirección automática HTTP→HTTPS cuando está activado (`HTTPS_REDIRECT=true`).
- **Almacenamiento de tokens**: httpOnly cookies en backend / cifrado AES con CryptoJS en localStorage como fallback en frontend.
- **Rate limiting**: Límites por IP y por usuario autenticado con almacenamiento distribuido en Redis.
- **Auditoría de dependencias**: `pip-audit`, `safety` y `npm audit` mediante `scripts/audit_dependencies.sh`.
- **Logs de seguridad**: Registro de eventos de autenticación y accesos denegados en `app.security`.

## Configuración en producción

### Variables de entorno

- `CORS_ORIGINS`: Lista de dominios permitidos, separados por comas (ej. `https://app.example.com`).
- `HTTPS_REDIRECT`: `true` para forzar HTTPS en producción.
- `JWT_SECRET_KEY`: Clave secreta para JWT (mínimo 32 caracteres).
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Tiempo de expiración del access token (por defecto 30 min).
- `JWT_REFRESH_TOKEN_EXPIRE_MINUTES`: Tiempo de expiración del refresh token (por defecto 7 días).

### Recomendaciones adicionales

- Configurar **HSTS** y cabeceras de seguridad en el servidor web (Nginx / Cloudflare).
- Usar **CSP** (Content Security Policy) para mitigar XSS.
- Mantener actualizadas las dependencias ejecutando `scripts/audit_dependencies.sh`.
- Realizar análisis periódicos de secretos y cabeceras con `scripts/security_scan.py`.

## Decisiones de dependencias

### `tar` en el frontend — sin override global a v7 (MOBILE-HARDENING)

El commit 19fa3ed añadió `"overrides": { "tar": "^7.5.20" }` para parchear
CVEs críticos de node-tar (GHSA-29xp-372q-xqph / CVE-2025-64118,
CVE-2026-23745, etc.), que **solo tienen fix en la línea 7.x**. El override
rompía `npx cap sync android`: tar@7 se anuncia ESM (`__esModule: true`) y el
import-default compilado con tslib de `@capacitor/cli@6` resolvía
`tar.default → undefined` (`extractTemplate()` fallaba).

Se decidió **eliminar el override global** y volver a `tar@6.2.1` (resolución
natural de `@capacitor/cli@6: ^6.1.11`) por análisis de exposición:

- `@capacitor/cli` es el **único consumidor** de `tar` en el árbol.
- Solo extrae su **plantilla interna de confianza**
  (`assets/...-template.tgz` incluida en el paquete npm) durante
  `cap add/update`. No procesa archivos tar de origen no confiable, que es el
  vector de todos los CVEs citados (path traversal, race condition, gzip bomb).
- Es tooling de desarrollo/CI: `tar` no viaja dentro del APK/AAB ni del bundle
  web.

Revisar al actualizar a Capacitor 7+ (su CLI ya usa tar moderno) o si aparece
cualquier nuevo consumidor de `tar` que procese entradas externas.

## Verificación

Ejecutar las herramientas de verificación de seguridad:

```bash
# Escaneo de seguridad (secretos y cabeceras)
python scripts/security_scan.py

# Auditoría de dependencias
bash scripts/audit_dependencies.sh

# Pruebas unitarias de seguridad
uv run pytest tests/security/
```
