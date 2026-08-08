# E2E manual — camino crítico (E2E.MANUAL.1)

**Fecha:** 2026-08-08
**Entorno:** local (Docker Compose: api + postgres:16 + redis)
**Tester:** run automatizado vía API (E2E.MANUAL.PASS.1)
**Build / commit:** `4091a0d` + fixes del run
**Resultado:** ✅ **PASS con SKIP** — detalle en
[`e2e_runs/2026-08-08_PASS.md`](e2e_runs/2026-08-08_PASS.md)

> **Modo personal.** Con `AUTH_DISABLED=true` + `NEXT_PUBLIC_AUTH_DISABLED=true`
> no hay registro ni login: la sección 1 se sustituye por su versión personal.
> Si pruebas con `AUTH_DISABLED=false`, usa la sección 1-bis (multiusuario).

## 0. Preflight

| # | Paso | PASS |
|---|------|------|
| 0.1 | `python scripts/check_integrations_ready.py` — jwt/db READY (smtp/firebase/proxy pueden BLOCKED) | ✅ exit 0 |
| 0.2 | `python scripts/smoke_es_providers.py` exit 0 | ✅ exit 0 |
| 0.3 | `python scripts/release_check.py --skip-smoke` PASSED | ✅ 1128 passed |
| 0.4 | API up (`/health` responde 200) | ✅ api/database/redis ok |
| 0.5 | Frontend up (dashboard o home **sin** forzar login) | ⏭️ SKIP — sin `node_modules`/navegador |

## 1. Auth — modo personal (`AUTH_DISABLED=true`)

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 1.1 | Abrir `http://localhost:3000/` | Redirige a `/dashboard`, app usable **sin** login | ⏭️ SKIP — código revisado, sin navegador |
| 1.2 | No aparece muro de login | `AuthGuard` deja pasar | ⏭️ SKIP — idem |
| 1.3 | `GET /api/v1/opportunities` **sin** token | **200** (no 401) | ✅ (era 401 → bug compose) |
| 1.4 | Google / Firebase | SKIP si no configurado | ⏭️ SKIP |

### 1-bis. Auth multiusuario (solo si `AUTH_DISABLED=false`)

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 1b.1 | Register o login en `/auth/login` | 200, tokens, redirección | ☐ |
| 1b.2 | Ruta protegida sin token | redirect login o 401 | ☐ |
| 1b.3 | (Opcional) Google login | SKIP si no hay Firebase | ☐ / SKIP |

## 2. Search → resultados

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 2.1 | Search query válida (ej. BMW) + AS24 | ≥1 resultado o empty state ES claro | ✅ 5 resultados (era 0 → bug URL) |
| 2.2 | Query absurda / sin hits | Empty state en **español** + hint (SEARCH.EMPTY.1) | ✅ 200 vacío + empty ES |
| 2.3 | Error de red (API caída) | Mensaje error ES, no stack | ⏭️ SKIP — opcional |

## 3. Drawer (vehículo)

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 3.1 | **Explanation** de mercado (MKT.2) | Texto ES no vacío si hay comparables | ✅ |
| 3.2 | **Fuentes** (`provider_sources`) (MKT.3) | Chips o lista | ✅ `["autoscout24"]` |
| 3.3 | **Score** (SCORE.1) | `category_label_es`, no solo código EN | ✅ 24 / "Malo" |
| 3.4 | **Profit / cost_lines** (PROFIT.1) | Partidas con `label_es` | ✅ 8 partidas ES |
| 3.5 | **coherence_warnings** (ROI.1) | Coherente con el caso | ✅ vacío y coherente |
| 3.6 | **Recomendación / riesgo** (REC.1) | `*_label_es` | ✅ "Descartar" / "Alto" |
| 3.7 | **Negociación** (NEG.1) | Apertura / defectos / mercado / Cierre en ES | ✅ 4 secciones ES |

> Verificado sobre el **payload de la API**; el render en navegador queda SKIP.

## 4. Opportunities

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 4.1 | Listado `/opportunities` | Items con labels ES (OPP.LIST.1) | ✅ 200 |
| 4.2 | Vacío | Empty ES aceptable | ✅ `total=0` |

## 5. Admin

| # | Paso | Esperado | PASS |
|---|------|----------|------|
| 5.1 | Admin status — bloque **Providers** (ADMIN.1b) | `registered` + flags + perfil | ✅ 4 providers, perfil SPAIN |
| 5.2 | Health compuesto | `checks.api` / `database` / `redis` coherentes | ✅ los tres `ok` |

## 6. Cierre

| Resultado global | ✅ **PASS con SKIP** (frontend en navegador, Firebase, proxy) |
|---|---|
| Commit | `4091a0d` + fixes E2E.MANUAL.PASS.1 |
| Bugs bloqueantes | 3 encontrados y corregidos (compose passthrough, URL de búsqueda AS24, email del usuario local) |
| Tests | 1128 passed; 11 de regresión nuevos |
| Notas | Detalle completo en `e2e_runs/2026-08-08_PASS.md` |

## Fuera de este checklist

- mobile.de live (A.5b), SMTP real, Firebase SA, AS24-ES live.
- Playwright/Cypress (task futuro TEST.E2E.1) — cubriría las filas SKIP de UI.
