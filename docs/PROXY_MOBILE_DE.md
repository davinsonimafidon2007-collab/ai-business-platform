# Runbook: mobile.de con proxy residencial / cookies

> **Estado esperado:** con proxy real (manual), el canary de mobile.de puede pasar a **PASS**.
> Sin proxy, mobile.de devuelve 403 anti-bot y el canary queda en **WARN** (no falla el job).

---

## 1. Contexto

mobile.de bloquea sistemáticamente peticiones desde IPs de datacenter con
HTTP 403 «Zugriff verweigert / Access denied». Para obtener HTML real hace
falta:

- **Proxy residencial** (recomendado) — IP de ISP real, no datacenter.
- **Cookies de navegador real** (alternativa/complemento) — sesión con
  consentimiento y cookies de un navegador que ya pasó el anti-bot.

El cliente HTTP (`app/providers/http_client.py`) ya soporta ambas vías y un
delay mínimo entre peticiones. **No hay cambios funcionales obligatorios en
los parsers** para activar el proxy; solo configuración.

---

## 2. Configuración (`.env`)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `PROVIDER_HTTP_PROXY` | Proxy residencial (HTTP/SOCKS5) | `http://user:pass@host:port` |
| `PROVIDER_HTTP_COOKIES` | Cookie header de navegador real (opcional) | `sid=abc123; consent=1` |
| `PROVIDER_HTTP_MIN_DELAY_MS` | Delay mínimo entre peticiones (ms) | `800`–`1500` en prod |

```env
# .env
PROVIDER_HTTP_PROXY=http://user:pass@residential-proxy.example:8080
PROVIDER_HTTP_COOKIES=
PROVIDER_HTTP_MIN_DELAY_MS=1000
```

> **Seguridad:** nunca commits de `.env` con credenciales reales. El código
> lee estas variables de entorno; no hay secretos hardcodeados.

---

## 3. Verificación manual con proxy real

```bash
# Desde la raíz del proyecto, con .env configurado
uv run python scripts/verify_providers_live.py

# Guardar HTML para revisar selectores si count=0
uv run python scripts/verify_providers_live.py --save-html $env:TEMP\provider_html
```

Salida esperada para mobile.de con proxy OK:

```
mobile_de: search: OK count=N
mobile_de: detail: OK brand=... model=... price=...
```

### Interpretación de fallos

| Síntoma | Causa | Acción |
|---------|-------|--------|
| `403 / ProviderConnectionError` | IP bloqueada por anti-bot | Configurar proxy residencial o cookies reales |
| `429 / ProviderRateLimitError` | Rate limit del provider | Subir `PROVIDER_HTTP_MIN_DELAY_MS` (800–1500) o proxy rotativo |
| `count=0` | Página llegó pero selectores no encuentran anuncios | Guardar HTML con `--save-html` y revisar selectores |

---

## 4. Canary (job programado)

El job `app/jobs/provider_canary.py` se ejecuta cada `PROVIDER_CANARY_INTERVAL`
(por defecto 6h; `0` = desactivado).

Comportamiento actual:

- **AutoScout24** — obligatorio. `0 listings` o error → **FAIL** del job.
- **mobile.de** — no bloquea el job. `403 anti-bot` → **WARN** (`mobile_status=blocked`).
  Con proxy real y `count>0` → **PASS** (`mobile_status=ok`).

### Cómo pasar mobile.de a PASS

1. Configurar `PROVIDER_HTTP_PROXY` (residencial) en `.env`.
2. Reiniciar la API (el scheduler arranca con la app).
3. Verificar con `scripts/verify_providers_live.py` que `search: OK count>0`.
4. El siguiente canary reportará `mobile_status=ok`.

---

## 5. Referencias de código

| Archivo | Rol |
|---------|-----|
| `app/providers/http_client.py` | Cliente HTTP con proxy/cookies/delay/retries |
| `app/providers/base.py` | `_get_client()` crea `ProviderHttpClient` con settings |
| `app/providers/mobile_de.py` | Provider mobile.de (selectores + detección anti-bot) |
| `app/jobs/provider_canary.py` | Canary: AS24 obligatorio, mobile.de WARN/PASS |
| `app/core/config.py` | Settings `provider_http_*` |
| `scripts/verify_providers_live.py` | Smoke script de verificación en vivo |