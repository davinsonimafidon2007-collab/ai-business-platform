# Runbook: mobile.de — activación segura y ligera (sin evasión anti-bot)

> **Defaults seguros:** `ENABLE_MOBILE_DE=false` + `ENABLE_MOBILE_DE_PLAYWRIGHT=false`
> (` .env.example:137-140`). El provider **no** se registra ni abre browser si no lo activas explícitamente.
> Mobile.de sin activar no gasta recursos ni intenta bypass. Con proxy/playwright desactivado el canary queda **WARN** (no falla el job); con proxy real o Playwright + HTML válido pasa a **PASS**. No se implementan mecanismos para eludir restricciones del proveedor: solo transporte configurable permitido.

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

## 2. Configuración (`.env`) — activación explícita

> **Comportamiento por defecto (seguro/ligero):**
> ```env
> ENABLE_MOBILE_DE=false
> ENABLE_MOBILE_DE_PLAYWRIGHT=false
> ```
> Con ambos en `false` el provider no se registra (`ProviderRegistry` no añade `mobile_de`), no se lanza browser ni se hace HTTP a mobile.de. Es el default de `.env.example`.

**Para activar explícitamente (requiere decisión consciente):**

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `ENABLE_MOBILE_DE` | Activa provider mobile.de (httpx) | `true` solo si tienes `PROVIDER_HTTP_PROXY` |
| `ENABLE_MOBILE_DE_PLAYWRIGHT` | Usa Playwright headless para mobile.de (JS, sin cuenta). Requiere `playwright install chromium` | `true` (fallback a httpx si no instalado) |
| `PROVIDER_HTTP_PROXY` | Proxy residencial (HTTP/SOCKS5) — opcional, método permitido | `http://user:pass@host:port` |
| `PROVIDER_HTTP_COOKIES` | Cookie header de navegador real (opcional) | `sid=abc123; consent=1` |
| `PROVIDER_HTTP_MIN_DELAY_MS` | Delay mínimo entre peticiones (ms) | `800`–`1500` en prod |
| `PLAYWRIGHT_TIMEOUT_MS` / `PLAYWRIGHT_HEADLESS` | Timeout/navegación Playwright | `30000` / `true` |
| `ENABLE_OPENCLAW_BROWSER` | Usa OpenClaw (agente externo) en vez de Playwright — ver ADR-006 | `true` solo si tienes `OPENCLAW_ENDPOINT` corriendo |
| `OPENCLAW_ENDPOINT` / `OPENCLAW_AGENT_ID` / `OPENCLAW_TIMEOUT_MS` | Servidor OpenClaw y agente especializado | `http://localhost:4173` / `mobile-de-browser` / `45000` |

```env
# .env — ejemplos de activación explícita (no por defecto)

# Opción A: httpx con proxy (tradicional)
ENABLE_MOBILE_DE=true
PROVIDER_HTTP_PROXY=http://user:pass@residential-proxy.example:8080
PROVIDER_HTTP_MIN_DELAY_MS=1000

# Opción B: Playwright headless (sin cuenta, con JS) — recomendado si quieres probar sin proxy
ENABLE_MOBILE_DE=true
ENABLE_MOBILE_DE_PLAYWRIGHT=true
PLAYWRIGHT_TIMEOUT_MS=30000
PLAYWRIGHT_HEADLESS=true
# Opcional: combinar con proxy
# PROVIDER_HTTP_PROXY=http://user:pass@residential-proxy.example:8080

# Opción C: OpenClaw como brazo de browser automation externo (ADR-006).
# Tiene prioridad sobre ENABLE_MOBILE_DE_PLAYWRIGHT si ambos están activos.
# Requiere un servidor OpenClaw real corriendo en OPENCLAW_ENDPOINT — no
# incluido en este repo, no verificado contra una instancia real todavía.
ENABLE_MOBILE_DE=true
ENABLE_OPENCLAW_BROWSER=true
OPENCLAW_ENDPOINT=http://localhost:4173
OPENCLAW_AGENT_ID=mobile-de-browser

# Opción D: mantener desactivado (default seguro)
ENABLE_MOBILE_DE=false
ENABLE_MOBILE_DE_PLAYWRIGHT=false
ENABLE_OPENCLAW_BROWSER=false
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
| `app/providers/mobile_de_playwright.py` | Delega en `get_browser_automation()` para el transporte browser |
| `app/providers/browser_automation.py` | Abstracción `BrowserAutomation` (Playwright / OpenClaw) — ver ADR-006 |
| `app/jobs/provider_canary.py` | Canary: AS24 obligatorio, mobile.de WARN/PASS |
| `app/core/config.py` | Settings `provider_http_*` y `openclaw_*` |
| `scripts/verify_providers_live.py` | Smoke script de verificación en vivo |