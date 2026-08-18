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
