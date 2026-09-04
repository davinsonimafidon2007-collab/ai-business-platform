# TASK_A_07 — Bloqueos externos encontrados en la auditoría MVP (no reparables en código)

## Contexto

Auditoría final del MVP (2026-09-04, commit base `b574f5d`) confirmó el
flujo de negocio completo (buscar → resultados → comparar → coste →
oportunidad → mostrarla) funcionando end-to-end **en vivo** contra
AutoScout24 (DE y ES) — verificado con peticiones reales, no fixtures.
Veredicto: **MVP READY WITH EXTERNAL PROVIDER BLOCKER**.

Los puntos de abajo NO son bugs de código: son recursos externos
(proxy, credenciales, una instancia real de OpenClaw) que esta sesión
no tiene disponibles. Se documentan aquí porque OpenClaw, al ser un
agente externo que puede tener acceso a recursos distintos (o poder
desplegar/configurar cosas que esta sesión no puede), podría avanzar
donde esta sesión no pudo. **No conviertas ninguno de estos puntos en
un "arreglo de código" — si no hay recurso externo disponible,
documenta el bloqueo y para ahí; no inventes bypass de anti-bot.**

---

## Bloqueo 1 — mobile.de: sin datos reales sin proxy/cookies/browser real

### Problema
`app/providers/mobile_de.py` y `app/providers/mobile_de_playwright.py`
son reales y correctos (URL building, parsing, detección de bloqueo),
pero **mobile.de devuelve HTTP 403 anti-bot** a cualquier petición desde
este entorno — confirmado en vivo durante la auditoría (petición real
de 11s, no un mock). Verificado también que **una sesión de navegador
interactiva normal (sin ninguna técnica de evasión) SÍ consigue pasar**
el bloqueo — sugiere que el bloqueo distingue tráfico headless/datacenter
de tráfico de navegador real, no que sea un bloqueo total.

### Lo que esta sesión NO puede hacer
- No tiene un proxy residencial disponible (`PROVIDER_HTTP_PROXY`).
- No tiene cookies de una sesión de navegador real y autorizada
  (`PROVIDER_HTTP_COOKIES`).
- No tiene una instancia de OpenClaw real corriendo a la que apuntar
  `OPENCLAW_ENDPOINT` (ver Bloqueo 3).

### Lo que SÍ podrías intentar (si tienes el recurso)
1. Si tienes acceso a un proxy residencial: configura
   `PROVIDER_HTTP_PROXY` en `.env` y valida con
   `uv run python scripts/verify_providers_live.py` (ver
   `docs/PROXY_MOBILE_DE.md`, sección 3).
2. Si tienes acceso a cookies de una sesión de navegador real y
   consentida: configura `PROVIDER_HTTP_COOKIES` igual.
3. Si puedes desplegar un OpenClaw browser-worker real (no headless
   puro, idealmente con un perfil de navegador persistente): ver
   Bloqueo 3 — esa es la vía ya preparada arquitectónicamente.

### Archivos relevantes
- `app/providers/mobile_de.py`, `app/providers/mobile_de_playwright.py`
- `docs/PROXY_MOBILE_DE.md`
- `app/core/config.py` (`provider_http_proxy`, `provider_http_cookies`)

### Criterio de aceptación
- `POST /api/v1/search` con `providers: ["mobile_de"]` y una URL real de
  mobile.de devuelve `results` no vacíos (no `provider_issues` con
  `ProviderConnectionError`).
- Si no lo consigues: documenta qué recurso probaste y por qué siguió
  bloqueado. No fuerces un "PASS" falso.

---

## Bloqueo 2 — coches.net: mismo problema, confirmado en vivo hoy

### Problema
`app/providers/coches_net.py` es un scraper real, probado contra un
fixture HTML capturado (2026-08-20). Pero en la auditoría de hoy,
probado en vivo, coches.net devolvió una página de reto anti-bot
(`<title>Ups! Parece que algo no va bien...</title>`,
`meta name="robots" content="noindex, nofollow"`) en vez de listados
reales — mismo patrón que mobile.de.

### Lo que SÍ podrías intentar
- Mismas opciones que Bloqueo 1 (`PROVIDER_HTTP_PROXY`/
  `PROVIDER_HTTP_COOKIES`), pero coches.net no tiene transporte
  Playwright/OpenClaw todavía — solo httpx (`app/providers/coches_net.py`).
  Si un proxy no basta, considera si merece la pena añadirle el mismo
  patrón de `BrowserAutomation` que ya tiene mobile.de (ver
  `app/providers/browser_automation.py`, ADR-006) — pero solo si
  confirmas primero que un navegador real SÍ pasa el bloqueo (como se
  confirmó para mobile.de), para no construir algo sin evidencia de que
  vaya a funcionar.

### Archivos relevantes
- `app/providers/coches_net.py`
- `tests/unit/providers/test_coches_net.py`
- `tests/fixtures/coches_net_sample.html` (fixture de referencia)

### Criterio de aceptación
- `POST /api/v1/search` con `providers: ["coches_net"]` devuelve
  `results` no vacíos para una marca real (ej. "seat").

---

## Bloqueo 3 — Validar OpenClawBrowserAutomation contra una instancia real

### Problema
`app/providers/browser_automation.py::OpenClawBrowserAutomation` está
implementado y probado con mocks (`tests/unit/test_browser_automation.py`),
pero **nunca se ha ejecutado contra un servidor OpenClaw real** — no
había ninguna instancia disponible en el entorno de esta sesión.

El contrato esperado es simple y ya está documentado en el código:

```
POST {OPENCLAW_ENDPOINT}/agents/{OPENCLAW_AGENT_ID}/fetch
Request:  {"url": "...", "wait_selector": "..." | null}
Response: {"status": "ok" | "blocked" | "error", "html": "..."}
```

### Lo que podrías hacer (tú sí tienes/puedes tener una instancia OpenClaw)
1. Levantar/exponer un servidor OpenClaw que implemente ese contrato
   (un agente `mobile-de-browser` que navegue con un browser real, no
   headless de datacenter — ver Bloqueo 1 sobre por qué eso importa).
2. Configurar en `.env`:
   ```
   ENABLE_OPENCLAW_BROWSER=true
   OPENCLAW_ENDPOINT=http://<tu-servidor-openclaw>
   OPENCLAW_AGENT_ID=mobile-de-browser
   ```
3. Validar con una búsqueda real de mobile.de (Bloqueo 1, criterio de
   aceptación) para confirmar que el navegador de OpenClaw SÍ pasa el
   bloqueo donde el Playwright headless del backend no.
4. Si funciona: documentarlo en `docs/PROXY_MOBILE_DE.md` (ya tiene la
   sección "Opción C" preparada) y en el ADR-006 (sección
   "Consecuencias") como validado, con evidencia real (timestamp,
   comando, resultado).
5. Si NO funciona: documenta el error real devuelto (no lo escondas) —
   `OpenClawBrowserAutomation` ya propaga `ProviderUnavailableError` con
   el motivo exacto.

### Archivos relevantes
- `app/providers/browser_automation.py`
- `docs/adr/0006-browser-automation-abstraction.md`
- `docs/PROXY_MOBILE_DE.md`

### Criterio de aceptación
- Al menos una ejecución real y documentada (no mock) de
  `OpenClawBrowserAutomation.fetch()` contra un servidor OpenClaw real,
  con resultado (éxito o fallo) registrado con evidencia.

---

## Bloqueo 4 — Firma real de Android (release)

### Problema
`frontend/android/app/build.gradle` (MOBILE-HARDENING #2) ya está
preparado para firmar con `keystore.properties` o variables de entorno
(`KEYSTORE_FILE`/`KEYSTORE_PASSWORD`/`KEY_ALIAS`/`KEY_PASSWORD`), y sale
sin firmar con un warning explícito si no hay credenciales — comprobado
en esta sesión: `.\gradlew.bat bundleRelease` compila correctamente pero
el AAB resultante no está firmado.

### Lo que NO se puede hacer sin el recurso
Generar o inventar un keystore de producción no es aceptable — tiene
que ser el keystore real del propietario de la cuenta de Google Play
(si existe) o uno nuevo generado y custodiado por el propietario del
proyecto, nunca por un agente.

### Lo que sí puedes hacer
- Si tienes acceso a un keystore real (o autorización para generar uno
  nuevo y comunicárselo de forma segura al propietario, nunca
  commitearlo): configura `keystore.properties` local o las variables
  de entorno de CI y valida `.\gradlew.bat bundleRelease` produce un AAB
  firmado (`jarsigner -verify` o el propio log de Gradle confirmando
  `signReleaseBundle` con firma real, no solo "exitoso sin firmar").

### Archivos relevantes
- `frontend/android/app/build.gradle`
- `frontend/keystore.properties.example` (si existe) / `.github/workflows/mobile-release-cicd.yml`

### Criterio de aceptación
- Un AAB de release firmado con un keystore real, verificable con
  `jarsigner -verify -verbose -certs app-release.aab`.
- Si no tienes el keystore: no se puede avanzar más aquí. No lo marques
  como resuelto.

---

## Regla general para estos 4 puntos

Si intentas cualquiera de estos y NO tienes el recurso externo
necesario, el resultado correcto es: **documentar el intento y el motivo
del bloqueo, no fingir que se resolvió.** Esta misma auditoría ya dejó
evidencia de que ninguno de estos 4 puntos es un defecto de código —
son, literal y exclusivamente, falta de un recurso externo (proxy,
cookies, instancia OpenClaw, keystore).
