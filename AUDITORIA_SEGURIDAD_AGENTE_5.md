# INFORME DE AUDITORÍA DE SEGURIDAD — AGENTE 5 (SEGURIDAD)

## Alcance
Directorio raíz, `app/core/security/` (no existe en raíz; sí en `ai-business-platform-clone`), `app/dependencies/auth.py`, `.env.example`, `frontend/src/app/services/auth/` (no existe como directorio; archivo suelto `google-auth.ts`), `docs/`, `GITHUB_SECRETS.md`.

---

## 1. JWT (`JWT_SECRET_KEY`, algoritmo, duración, refresh tokens)

| Componente | Estado / Evidencia |
|------------|-------------------|
| `JWT_SECRET_KEY` | `.env.example:18` vacío (`JWT_SECRET_KEY=`). `app/core/config.py:24` define `jwt_secret_key: str = ""`. Validación en `app/core/config.py:62-67`: debe ser >= 32 caracteres (o se lanza `ValueError`). **No hay secreto real expuesto en código ni en `.env.example`**. |
| `JWT_ALGORITHM` | `app/core/config.py:25`: `jwt_algorithm: str = "HS256"`. `app/services/auth_service.py:90`: `jwt.encode(..., algorithm=settings.jwt_algorithm)`. `refresh_token_service.py:42`: `jwt.decode(..., algorithms=[settings.jwt_algorithm])`. |
| Duración access token | `app/core/config.py:175`: `jwt_access_token_expire_minutes: int = 30`. `auth_service.py:81-89`: `timedelta(minutes=settings.jwt_access_token_expire_minutes)`. |
| Duración refresh token | `app/core/config.py:176`: `jwt_refresh_token_expire_minutes: int = 60 * 24 * 7` (7 días). `refresh_token_service.py:30-36`: `timedelta(minutes=settings.jwt_refresh_token_expire_minutes)`. |
| Refresh tokens (`refresh_token.py`) | `app/models/refresh_token.py`: tabla `refresh_tokens`. `token` (hash SHA-256), `user_id`, `is_revoked`, `expires_at`, `created_at`, `revoked_at`. **No almacena el token en texto plano** (`_hash_token` usa `hashlib.sha256`). |
| `refresh_token_service.py` | `refresh_token_service.py:22`: `_hash_token` (SHA-256 determinista). `create_refresh_token` (`line 29-38`) genera JWT con `type="refresh"`. `validate_refresh_token` (`line 58-73`) verifica firma, tipo, `is_revoked`, `expires_at`. `revoke_refresh_token` (`line 75-76`) revoca por hash. `decode_refresh_token` (`line 40-47`) valida `type == "refresh"`. |
| `auth_service.py` (refresh) | `auth_service.py` no maneja refresh directamente; delega a `RefreshTokenService`. `decode_access_token` (`line 92-109`) intenta claves actuales y `jwt_previous_secrets` (`line 98`). **Rotación soportada**. |
| `dependencies/auth.py` | `get_current_user` (`line 23-72`) soporta JWT Bearer (`security = HTTPBearer(auto_error=False)`). No retorna `None` (lanza `AuthenticationError`). `require_role` (`line 75-81`) y `require_permission` (`line 87-103`) para roles (`ADMIN`, `USER`) y permisos (`search`, `manage_users`, etc.). |

**Observaciones:**
- No hay `refresh_token` con rotación automática de secretos en refresh (usa `jwt_secret_key` actual, no `previous_secrets` para refresh — esto es consistente porque `refresh_token_service.py` solo usa `settings.jwt_secret_key`, no la lista de previas). Esto podría ser un problema si `jwt_secret_key` rota: los refresh tokens antiguos dejarían de ser válidos inmediatamente (porque `decode_refresh_token` no prueba claves previas). **Recomendación:** agregar `jwt_previous_secrets` al decode de refresh, igual que `auth_service.py`.

---

## 2. Autenticación (`register`, `login`, `google`): contraseñas, hash de API keys

| Archivo | Evidencia |
|---------|-----------|
| `register` | `app/api/v1/auth.py:59-67`: `register_user` llama `service.register_user(email=str(payload.email), password=payload.password)`. |
| `login` | `app/api/v1/auth.py:70-92`: `authenticate_user(email=..., password=...)` verifica `password_hasher.verify(password, user.hashed_password)`. Si falla (`UnknownHashError` o `is_valid_password == False`), lanza `InvalidCredentialsError`. |
| `google` | `app/api/v1/auth.py:95-110`: `authenticate_with_google(id_token=payload.id_token)` verifica token Firebase (`verify_google_id_token`). Crea usuario con `hashed_password=password_hasher.hash(secrets.token_urlsafe(32))`. No guarda token de Google ni email en texto plano en DB (el email viene del payload). |
| Contraseñas (`pwdlib`, `Argon2`) | `app/services/auth_service.py:17`: `password_hasher = PasswordHash.recommended()` (`pwdlib` con Argon2). `register_user` (`line 29`): `hashed_password = password_hasher.hash(password)`. `authenticate_user` (`line 39`): `password_hasher.verify(password, user.hashed_password)`. |
| Hash de claves API | `app/services/api_key_service.py:13`: `password_hasher = PasswordHash.recommended()`. `hash_api_key` (`line 33-35`): `password_hasher.hash(api_key)`. `validate_api_key` (`line 68-94`): compara con `password_hasher.verify(api_key, candidate.key_hash)`. **No guarda la clave en texto plano**. |

**Observaciones:**
- No hay contraseñas en texto plano en código ni en DB (ORM usa `hashed_password` y `key_hash`).
- No hay logs que impriman `password`, `token` o `hashed_password` en `auth_service.py`.

---

## 3. Autorización: roles, permisos, middleware

| Componente | Estado / Evidencia |
|------------|-------------------|
| Roles (`ADMIN`, `USER`) | `app/models/role.py:4-5`: `Role(str, Enum)` con `ADMIN = "admin"`, `USER = "user"`. |
| Middleware (`authentication_middleware.py`) | `app/middleware/authentication_middleware.py:34-89`: `AuthenticationMiddleware`. Salta auth para `PUBLIC_PATHS` (`line 19-31`) que incluye `/auth/*`, `/health`, `/docs`, etc. `request.state.user` se setea si JWT/API Key es válida. Si `settings.auth_disabled` (`line 53`), salta por completo (`call_next` directo). **Nota crítica:** `auth_disabled=true` en producción sin `ALLOW_AUTH_DISABLED_IN_PROD` lanza `ValueError` (`app/core/config.py:124-134`). |
| Middleware (`admin_middleware.py`) | **No existe** en el directorio raíz (`glob` no encontró `admin_middleware.py`). La protección de rutas `/api/v1/admin/*` se hace exclusivamente por dependencias (`require_admin`, `require_permission`) en `app/dependencies/auth.py`. Esto es funcional (el middleware salta `pre-auth` para `/api/v1/admin/` en `authentication_middleware.py:60-61`, dejando la protección al dependency layer). |
| Endpoints públicos vs protegidos | `public_paths` (`authentication_middleware.py:19-31`): `/health`, `/docs`, `/redoc`, `/openapi.json`, `/api/v1/auth/*` (register, login, refresh, google, forgot-password, reset-password). **Todos los demás endpoints requieren JWT o API Key** (o `auth_disabled`). |
| `admin/*` endpoints | `app/api/v1/admin_api_keys.py`, `admin_feature_flags.py`, `admin_metrics.py`, `admin_status.py`: todos usan `Depends(require_admin)` o `require_permission(...)`. Ej. `admin_api_keys.py:25`: `current_user: User = Depends(get_current_user)` y luego verificación de permiso (`line 46-48`). |

**Observaciones:**
- No existe middleware `admin_middleware.py`; la autorización es por dependencias (FastAPI `Depends`). Esto es aceptable, pero no hay una capa de middleware unificada que valide `request.state.user` para admin (solo `get_current_user` y `require_role`).

---

## 4. CORS (`CORS_ORIGINS`, `CORS_ALLOW_HEADERS`)

| Configuración | Evidencia |
|---------------|-----------|
| `.env.example` | `CORS_ORIGINS=http://localhost:3000,...` (`.env.example:35`). `CORS_ALLOW_HEADERS=*` (`.env.example:40`). `CORS_ALLOW_CREDENTIALS=true` (`.env.example:36`). |
| `app/core/config.py` (`.env` en raíz) | `cors_origins` (`line 177`): lista por defecto con localhost/capacitor. `cors_allow_headers` (`line 180`): lista explícita (`Authorization,Content-Type,...`). `validate_cors_for_env` (`line 137-174`): en `production` rechaza `*` en origins, rechaza solo dev-like origins, y endurece `*` en headers. **Esto es una protección activa**. |
| `ai-business-platform-clone/app/core/config.py` | Similar (`line 215-218`), con `https_redirect` y `security_headers_enabled` adicionales (`line 181-196`). |

**Observaciones:**
- En desarrollo (`development` o `test`) `CORS_ALLOW_HEADERS=*` no se endurece automáticamente (solo en `production`). Esto es correcto para DX local, pero debe vigilarse en despliegues de staging con `ENVIRONMENT=production`.

---

## 5. CSRF: ¿hay protección? ¿cookies con `HttpOnly`/`Secure`?

| Componente | Estado / Evidencia |
|------------|-------------------|
| CSRF | **No existe protección CSRF explícita** (`grep` para `csrf` o `CSRF` no encontró nada en `app/`, `frontend/src/`). No hay `csrf_token` en headers ni cookies. |
| Cookies (`HttpOnly`/`Secure`) | No hay uso de cookies para autenticación. El JWT se transporta por `Authorization: Bearer` o `X-API-Key`. `frontend/src/app/services/storage.ts`: usa `localStorage` (`SECURE_PREFIX = "abp_secure_"`) con `encode` (`btoa`/`Buffer`) y `decode`. **No es `HttpOnly` ni `Secure`** (no aplica a `localStorage`). No hay cookies de sesión. |

**Observaciones:**
- No hay CSRF porque el backend no usa cookies para autenticación (solo Bearer / API Key). Esto es aceptable para APIs REST sin cookies, pero el frontend almacena tokens en `localStorage`, lo que expone a XSS (ver sección 6).

---

## 6. XSS: ¿headers `Content-Security-Policy`? ¿sanitización en frontend?

| Componente | Estado / Evidencia |
|------------|-------------------|
| `Content-Security-Policy` (CSP) | **No existe** en el proyecto raíz (`grep` `Content-Security-Policy` encontró solo referencias en `ai-business-platform-clone/app/core/config.py:195`). `security_headers_enabled` (`line 191`) y `security_middleware.py` (`ai-business-platform-clone/app/middleware/security_middleware.py`) no están montados en el proyecto raíz (`main.py` del raíz no incluye `security_middleware`). |
| `X-XSS-Protection` | Solo en `ai-business-platform-clone/app/middleware/security_middleware.py:98` (`X-XSS-Protection: 1; mode=block`). **No en raíz**. |
| Sanitización frontend | No hay sanitización explícita (`sanitize`, `dompurify`, `escape`) en `frontend/src/`. El frontend usa Next.js / React, que hace escaping automático en JSX, pero no hay CSP ni headers de seguridad configurados en la app raíz. |

**Observaciones:**
- El middleware `security_middleware.py` (`ai-business-platform-clone`) aplica `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection`, `Strict-Transport-Security` (`HSTS`). Pero este archivo no está integrado en `app/main.py` del directorio raíz. **Recomendación:** montar `security_middleware` en `main.py` (o importar del clone) para que las cabeceras se apliquen.

---

## 7. SQL Injection: ¿parámetros bindados? ¿consultas crudas (`text()`) sin sanitización?

| Componente | Evidencia |
|------------|-----------|
| ORM / parámetros bindados | Todo el código usa `SQLAlchemy` (`AsyncSession`, `select`, `update`, `delete`) con modelos ORM (`app/models/`). No hay interpolación de strings en consultas SQL. |
| `text()` crudas | `app/database/manager.py:199`: `__import__("sqlalchemy").text("SELECT 1")`. `app/api/v1/routes/health.py:46`: `text("SELECT 1")`. Ambas son constantes literales sin parámetros de usuario. **No hay riesgo de SQL Injection**. |

---

## 8. Secrets: `.env.example`, `.gitignore`, exposición en código/logs

| Componente | Estado / Evidencia |
|------------|-------------------|
| `.gitignore` | `.gitignore:38-39`: `.env`, `.env.*` ignorados. `.env.example` (`!` en `.gitignore`) sí se versiona. `GITHUB_SECRETS.md` no contiene valores de secrets. |
| `.env.example` | No contiene valores reales (`JWT_SECRET_KEY=` vacío, `DATABASE_URL` con credenciales ficticias `postgres:postgres`, `SMTP_PASSWORD=` vacío). **No hay exposición de secrets reales**. |
| Exposición en código | `app/scripts/verify_providers_live.py:11`: `export JWT_SECRET_KEY='test_secret_key_that_is_at_least_32_characters_long_xx'`. Es un valor explícito de prueba (`test_...`), no un secret real de producción. `app/core/config.py:54-59`: `test_secret_key_that_is_at_least_32_characters_long_1234567890` (para `environment=test`). **Estos son valores de test, no secrets reales expuestos**. |
| Logs sensibles | `app/services/audit_service.py:67`: `details=f"Failed login attempt for email: {email}"` — **log de email** (dato sensible). No hay logs de contraseñas (`password`), tokens (`token`), ni `hashed_password`. `app/middleware/logging_middleware.py:62-85`: no loguea `request.body` ni `response.body` (`log_request_body=False`, `log_response_body=False`). No hay contraseñas ni tokens en logs de middleware. |
| `GITHUB_SECRETS.md` | `GITHUB_SECRETS.md:7-18`: documenta `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `API_URL`, `FIREBASE_CREDENTIALS_JSON`. No expone valores reales. **Seguridad documental adecuada**. |

**Observaciones:**
- `audit_service.py` guarda `email` en logs de `login_failed`. Esto es un riesgo de exposición de PII (email) en logs. **Recomendación:** eliminar `email` del detalle de auditoría, o usar un hash/anónimo.

---

## 9. Almacenamiento de tokens (cookies, localStorage, secureStorage)

| Componente | Estado / Evidencia |
|------------|-------------------|
| Frontend (`localStorage`) | `frontend/src/app/services/storage.ts`: `secureStorage` usa `window.localStorage.getItem(SECURE_PREFIX + key)` (`line 51`) y `window.localStorage.setItem(...)` (`line 68`). `encode` (`line 21-26`) usa `btoa` (`base64`). **No es `HttpOnly` ni `Secure`**. `auth-store.ts` (`line 8-12`): `TOKEN_KEYS` (`accessToken`, `refreshToken`, `user`). `setSession` (`line 67-71`) guarda en `secureStorage`. `initialize` (`line 79-115`) lee de `secureStorage`. |
| Nativo (`Capacitor Preferences`) | `storage.ts:41-48`: usa `Preferences.get({ key })` en nativo (`Capacitor.isNativePlatform()`). Esto es más seguro que `localStorage` en web, pero sigue sin ser `HttpOnly`. |
| `localStorage` expuesto a XSS | Si hay XSS, `localStorage.getItem("abp_secure_access_token")` puede ser robado. No hay protección `HttpOnly`. **Recomendación:** para mayor seguridad, usar cookies `HttpOnly` + `Secure` + `SameSite=Strict` para el refresh token (o al menos para el access token), aunque esto requiere cambios en el backend y CORS. |

---

## 10. HTTPS: ¿requerido en producción? ¿`TRUSTED_HOSTS`?

| Componente | Estado / Evidencia |
|------------|-------------------|
| `TRUSTED_HOSTS` | **No existe** en `app/core/config.py` del raíz ni en `.env.example`. No hay validación de `Host` header. |
| HTTPS obligatorio | `.env.example` no menciona `HTTPS_REDIRECT`. `app/core/config.py` (raíz) **no tiene** `https_redirect` ni `security_headers_enabled`. En `ai-business-platform-clone/app/core/config.py` (`line 181-196`) sí existen (`https_redirect`, `security_headers_enabled`), pero **no están montados en el proyecto raíz** (`app/main.py` no incluye `security_middleware`). |
| `security_headers_enabled` | Solo en `ai-business-platform-clone`. `security_middleware.py` (`line 70-101`) aplica `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection`, `Strict-Transport-Security` (`HSTS`). **No está integrado en raíz**. |

**Observaciones:**
- No hay `TRUSTED_HOSTS`. No hay redirección HTTPS obligatoria (`https_redirect` no montado). **Recomendación:** integrar `security_middleware` (o al menos `TRUSTED_HOSTS` y `https_redirect`) en `main.py` para producción.

---

## 11. Rate limiting (`rate_limit_middleware.py`, Redis / memoria)

| Componente | Estado / Evidencia |
|------------|-------------------|
| Middleware | `app/middleware/rate_limit_middleware.py:67-170`: `RateLimitMiddleware`. |
| Límites por rol | `ROLE_RATE_LIMITS` (`line 50-53`): `ADMIN` → `settings.rate_limit_premium` (120), `USER` → `settings.rate_limit_user` (30). `DEFAULT_RATE_LIMIT` (`line 56`): `settings.rate_limit_global` (60). |
| Límites por endpoint | `line 116-121`: `/api/v1/auth/login` (`POST`) → `rate_limit_login` (5), `/register` (`POST`) → `rate_limit_register` (10). |
| Headers `X-RateLimit-*` | `line 21`: `RATE_LIMIT_MODE_HEADER = "X-RateLimit-Mode"`. `line 169`: `response.headers[RATE_LIMIT_MODE_HEADER] = self._mode`. `line 241-244`: `Retry-After` y `X-RateLimit-Mode` en respuesta 429. **No hay `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`** (solo `Mode` y `Retry-After`). |
| Redis / memoria | `line 187-209`: `get_redis()` primero; si falla (`RedisError`, `RuntimeError`), cae a memoria local (`local_bucket`). `line 203-208`: `self._mode = "memory"`; log visible en producción (`line 179-185`: `logger.error(...)` throttled a ~1 log/10s). |

**Observaciones:**
- Falta `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. **Recomendación:** agregar estos headers para cumplir con estándares de rate limiting.
- El límite por `api_key` (`line 145-157`) usa `request.headers.get("X-API-Key", "")[:16]` como clave. Esto podría ser vulnerable a colisión de prefijos si el prefijo es fijo (`abp_live_`) y solo los primeros 16 chars del header se usan. **Recomendación:** usar el hash completo o el `api_key_id` en lugar de los primeros 16 caracteres del header.

---

## 12. API keys (`api_key.py`, `api_key_service.py`): hash (`pwdlib`), verificación

| Componente | Estado / Evidencia |
|------------|-------------------|
| Modelo (`api_key.py`) | `app/models/api_key.py`: `key_hash` (`String(255)`), `prefix` (`String(20)`), `scopes`, `expires_at`, `is_active`, `last_used_at`. |
| Servicio (`api_key_service.py`) | `generate_api_key` (`line 20-31`): `secrets.token_urlsafe(settings.api_key_length)` (`32`). `hash_api_key` (`line 33-35`): `password_hasher.hash(api_key)`. `validate_api_key` (`line 68-94`): lista candidatos por `prefix`, compara con `password_hasher.verify()`. `deactivate_api_key` (`line 112-114`): `is_active = False`. |
| Endpoint (`api_keys.py`) | `app/api/v1/api_keys.py`: rutas `/auth/api-keys`. `create_api_key` (`line 54-68`) devuelve `ApiKeyCreated` con `api_key` (texto completo) una sola vez. `revoke_api_key` (`line 95-106`) revoca. `list_api_keys` (`line 72-78`) lista las propias del usuario. `get_api_key` (`line 82-90`) obtiene por `api_key_id`. |

**Observaciones:**
- El hash usa `pwdlib` (`Argon2`), no `sha256` como los refresh tokens. Esto es más seguro.
- El `prefix` es fijo (`abp_live_`) y la clave completa se muestra solo una vez (`create_api_key`). Después, solo se guarda el hash. Esto es correcto.

---

## 13. Endpoints públicos vs protegidos

| Endpoint | Protección | Evidencia |
|----------|-----------|-----------|
| `/health`, `/health/live` | Pública (`public_paths`) | `authentication_middleware.py:19-21` |
| `/docs`, `/redoc`, `/openapi.json` | Pública | `authentication_middleware.py:22-24` |
| `/api/v1/auth/*` | Pública (no requiere JWT en middleware) | `authentication_middleware.py:25-30` |
| `/api/v1/admin/*` | Protegida por `require_admin` (middleware salta `pre-auth`, pero `get_current_user` y `require_role` aplican en la ruta) | `authentication_middleware.py:60-61`, `dependencies/auth.py:84` (`require_admin`) |
| Todos los demás (`/api/v1/*`) | Requiere JWT (`Bearer`) o `X-API-Key`, o `auth_disabled` | `authentication_middleware.py:65-87` |

---

## 14. Logs sensibles: contraseñas, tokens, emails

| Archivo | Evidencia | Riesgo |
|---------|-----------|--------|
| `audit_service.py:67` | `details=f"Failed login attempt for email: {email}"` | **Email expuesto en logs de auditoría** (PII). |
| `auth_service.py` | No imprime `password`, `token`, `hashed_password`. | Ninguno. |
| `refresh_token_service.py` | No imprime `token` ni `hash`. | Ninguno. |
| `api_key_service.py` | No imprime `api_key` completo (solo `prefix` y `name`). `create_api_key` (`line 45-65`) no loguea `full_key`. | Ninguno (pero `full_key` se devuelve al cliente una vez; si el cliente lo loguea, es responsabilidad del cliente). |
| `logging_middleware.py` | No loguea `request.body` ni `response.body`. `query` (`line 68`) sí se loguea (`str(request.url.query)`). Esto podría exponer parámetros sensibles en URL (ej. `?token=...`). **Recomendación:** excluir `query` o sanitizarlo para endpoints sensibles (`/auth/refresh`, `/auth/login`). |

---

## 15. Herramientas de seguridad (`npm audit`, `pip-audit`, `gitleaks`, `trufflehog`)

| Herramienta | Resultado / Evidencia |
|-------------|----------------------|
| `npm audit` | Ejecución exitosa (`npm audit --audit-level=moderate`). **1 vulnerabilidad alta (`brace-expansion`)** (`GHSA-rgw5-rvv9-x895`). `node_modules/brace-expansion`. **Recomendación:** `npm audit fix`. |
| `pip-audit` | No disponible (`python: No module named pip_audit`). No se pudo ejecutar. |
| `pyproject.toml` (dependencias Python) | `fastapi>=0.115.0`, `pydantic>=2.0.0`, `pwdlib[argon2]>=0.2.0`, `python-jose[cryptography]>=3.3.0`, `slowapi>=0.1.9`, `redis>=5.0.0`. No hay vulnerabilidades conocidas reportadas explícitamente en el archivo, pero `python-jose` ha tenido problemas históricos con `cryptography`. **Recomendación:** revisar `python-jose` y `pwdlib` periódicamente. |
| `gitleaks` | No disponible (`Get-Command` no encontró `gitleaks`). No se pudo ejecutar. |
| `trufflehog` | No disponible (`Get-Command` no encontró `trufflehog`). No se pudo ejecutar. |

---

## 16. Resumen de hallazgos críticos y recomendaciones

### Hallazgos críticos / altos
1. **No hay `security_middleware` montado en `main.py`** (`XSS-Protection`, `CSP`, `HSTS`, `X-Frame-Options`, `Referrer-Policy` faltan en raíz). Aunque existe en `ai-business-platform-clone/app/middleware/security_middleware.py`, no está integrado.
2. **No hay protección CSRF** (aunque no se usan cookies para JWT, el frontend usa `localStorage`).
3. **Tokens almacenados en `localStorage`** (`abp_secure_` prefix) — expuestos a XSS. No hay `HttpOnly` ni `Secure` cookies.
4. **`TRUSTED_HOSTS` no configurado** ni `https_redirect` montado.
5. **`audit_service.py` guarda `email` en logs** (`login_failed`).
6. **`npm audit`: vulnerabilidad alta `brace-expansion`**.
7. **Rate limit por `api_key` usa los primeros 16 chars del header** (`request.headers.get("X-API-Key", "")[:16]`) — posible colisión.
8. **`refresh_token_service.py` no prueba `jwt_previous_secrets`** al decodificar refresh tokens (a diferencia de `auth_service.py`). Si `jwt_secret_key` rota, los refresh tokens se invalidan inmediatamente.
9. **`CORS_ALLOW_HEADERS` en `.env.example` es `*`**; aunque `validate_cors_for_env` endurece en `production`, en `development` se mantiene `*`.
10. **No hay `Content-Security-Policy` (`CSP`)** en el proyecto raíz.

### Recomendaciones (priorizadas)
- **Alta:** Montar `security_middleware` (`HTTPSRedirectMiddleware`, `SecurityHeadersMiddleware`) en `app/main.py` del proyecto raíz (o importar desde `ai-business-platform-clone`).
- **Alta:** Eliminar `email` del detalle de `audit_service.log_login_failed` (o reemplazar por hash/anónimo).
- **Alta:** Aplicar `npm audit fix` para `brace-expansion`.
- **Media:** Agregar `jwt_previous_secrets` al `decode_refresh_token` (`refresh_token_service.py`).
- **Media:** Configurar `TRUSTED_HOSTS` y `https_redirect` (`True` en producción) en `app/core/config.py`.
- **Media:** Considerar migrar tokens de `localStorage` a cookies `HttpOnly` + `Secure` + `SameSite=Strict` (requiere cambios en frontend, `auth_store`, y backend para leer cookies).
- **Baja:** Agregar headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` en `rate_limit_middleware.py`.
- **Baja:** Revisar `pip-audit` periódicamente (`python-jose`, `pwdlib`, `redis`).

---

## Notas finales (sin revelar secrets)
- **No se encontraron secrets reales expuestos** en código fuente (`.env`, `.gitignore` protege `.env`). `GITHUB_SECRETS.md` no expone valores. `test_secret_key` (`app/scripts/verify_providers_live.py`) es un valor de prueba explícito.
- **No hay contraseñas ni tokens en texto plano** en código ni en DB (`hashed_password`, `key_hash`, `token` hash con SHA-256 o Argon2).
- **No hay `gitleaks` ni `trufflehog` disponibles** en el entorno; no se pudo realizar escaneo automático de secrets en el repositorio. Se recomienda instalar `trufflehog` o `gitleaks` y ejecutarlos periódicamente.
