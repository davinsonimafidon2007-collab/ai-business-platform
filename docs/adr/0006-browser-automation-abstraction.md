# ADR-006: Abstracción de browser automation (Playwright / OpenClaw)

- Estado: Aceptado
- Fecha: 2026-09-04
- Área: Providers / mobile.de / browser automation

## Contexto

`MobileDePlaywrightProvider` (`app/providers/mobile_de_playwright.py`) ya
soportaba un transporte con navegador headless (Playwright/Chromium) como
alternativa a httpx puro cuando mobile.de bloquea peticiones datacenter
(ver `docs/PROXY_MOBILE_DE.md`). La lógica de lanzar/cerrar el browser,
construir el contexto (proxy, cookies, user-agent) y navegar vivía
hardcodeada dentro de ese provider, acoplada directamente al paquete
`playwright`.

Surgió la necesidad de poder usar **OpenClaw** (un agente externo de
automatización de navegador, corriendo fuera del proceso de la API) como
transporte alternativo — y, potencialmente en el futuro, otros backends de
browser automation. Acoplar `MobileDeProvider` a un backend concreto de
cada vez habría significado reescribir la misma lógica de fallback/
detección anti-bot por cada nuevo backend.

## Decisión

Se introduce `app/providers/browser_automation.py`:

- `BrowserAutomation` (Protocol): contrato mínimo — `fetch(url, *,
  wait_selector=None) -> str`. Ninguna implementación bypassa anti-bot
  (sin CAPTCHA solving, sin stealth, sin fingerprint spoofing): solo
  devuelve el HTML que el navegador ve, igual que hacía httpx.
- `PlaywrightBrowserAutomation`: la lógica que antes vivía en
  `MobileDePlaywrightProvider`, extraída sin cambiar comportamiento.
- `OpenClawBrowserAutomation`: cliente HTTP puro contra un agente OpenClaw
  externo configurable (`OPENCLAW_ENDPOINT`/`OPENCLAW_AGENT_ID`). Habla un
  contrato JSON simple (`POST {endpoint}/agents/{agent_id}/fetch` →
  `{status, html}`); no importa ningún SDK de OpenClaw ni de Claude.
- `get_browser_automation(settings, *, user_agent=None)`: factory que
  selecciona el backend — OpenClaw (si `enable_openclaw_browser` y
  `openclaw_endpoint` configurados) → Playwright (si
  `enable_mobile_de_playwright`) → `None` (fallback a httpx puro, sin
  cambios respecto al comportamiento anterior a este ADR).

`MobileDePlaywrightProvider._download_url` ahora delega en
`get_browser_automation()` en vez de importar `playwright` directamente.
Si el backend elegido no está disponible (`ProviderUnavailableError`) o
falla por cualquier otra razón, cae a httpx — mismo contrato que antes.

### Por qué NO se acopla el dominio a "Claude" ni a un browser concreto

El "Claude Chrome" disponible en una sesión de Claude Code (el navegador
interactivo que un agente puede controlar turno a turno) **no es un
servicio HTTP persistente** al que este backend pueda llamar en runtime —
por eso no existe (ni tiene sentido que exista) un
`ClaudeBrowserAutomation`. Si en el futuro existe un servicio real
equivalente (p. ej. un servidor CDP local), se añade como una tercera
implementación de `BrowserAutomation` sin tocar `MobileDeProvider` ni el
resto del dominio — ese es exactamente el propósito de la abstracción.

## Justificación

- Playwright y OpenClaw son intercambiables sin duplicar la lógica de
  mobile.de (construcción de URL, parsing, detección anti-bot vía
  `_raise_if_blocked`), que sigue viviendo únicamente en
  `MobileDeProvider`/`MobileDePlaywrightProvider`.
- OpenClaw es una capa estrictamente opcional: `ENABLE_OPENCLAW_BROWSER`
  por defecto `false`, sin endpoint configurado. Si está apagado, mal
  configurado o no responde, el sistema sigue funcionando exactamente
  igual que antes de este ADR (Playwright si está activo, si no httpx).
- `OpenClawBrowserAutomation` nunca fabrica un HTML de respuesta: cualquier
  fallo (no configurado, timeout, HTTP error, `status != "ok"`, sin campo
  `html`) levanta `ProviderUnavailableError` para que el caller decida el
  fallback — nunca se disfraza un fallo como "0 resultados".

## Consecuencias

- Nuevas variables de entorno: `ENABLE_OPENCLAW_BROWSER`,
  `OPENCLAW_ENDPOINT`, `OPENCLAW_AGENT_ID`, `OPENCLAW_TIMEOUT_MS` (ver
  `.env.example`, `docker-compose.yml`).
- El contrato HTTP de `OpenClawBrowserAutomation` está definido y probado
  con mocks (`tests/unit/test_browser_automation.py`), pero **no
  verificado contra una instancia real de OpenClaw** — no hay una
  disponible en el entorno de desarrollo/CI actual. Queda como validación
  pendiente antes de depender de OpenClaw en producción.
- Los 7 tests existentes de `test_mobile_de_playwright_provider.py` siguen
  pasando sin modificar — la refactorización no cambió comportamiento
  observable de Playwright.

## Alternativas

- Acoplar `MobileDePlaywrightProvider` directamente a un cliente OpenClaw
  concreto (rechazada: repetiría la lógica de fallback/anti-bot por cada
  backend nuevo, y ataría el provider a un paquete/SDK externo).
- Un único "super-provider" que decida HTTP vs. browser vs. OpenClaw
  internamente (rechazada: mezclaría selección de transporte con lógica
  de dominio de mobile.de, dificultando testear cada capa por separado).
