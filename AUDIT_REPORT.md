# AUDITORÍA MULTI-AGENTE — AI BUSINESS PLATFORM

**Proyecto:** `C:\Users\davin\Documents\Default Project` (FastAPI + Next.js + Capacitor/Android + PostgreSQL/Redis)
**Fecha:** 2026-08-20
**Head raíz verificado:** `d3808b5` · **origin/main:** `e0f6724`
**Modalidad:** READ-ONLY (ningún archivo fue modificado; los tests/builds ejecutados no alteraron el repositorio)
**Repositorio auditado:** https://github.com/davinsonimafidon2007-collab/ai-business-platform.git

**Agentes ejecutados (13):** Backend · Frontend · Mobile · Base de datos · Seguridad · Testing(QA) · DevOps · Funcionalidad de negocio · Proveedores · Arquitectura · Documentación · Producto · Coordinador.

---

## 1) RESUMEN EJECUTIVO

El proyecto es una **aplicación web+API real, parcialmente implementada, con una app móvil Android que hoy NO compila**.

- El **backend** tiene una arquitectura sólida (routers funcionales, servicios con DI, 1.348 tests unitarios pasando al 100%, cobertura del 98% en los módulos que son gate de CI, `docker compose up` verificado en vivo con API 200).
- El **flujo de búsqueda + análisis** (AutoScout24 DE/ES reales → scoring → mercado → profit → recomendación) funciona de punta a punta en memoria y es la demo tecnológica real del producto.
- Sin embargo, **los flujos de negocio posteriores están rotos o fabricados**, con evidencia dura:
  - Crear un **deal** desde una búsqueda → **500** (se envía `external_id` donde el backend exige UUID con FK).
  - Simular beneficio / iniciar inspección → **404** (mismo desajuste de IDs).
  - La pantalla de **Oportunidades pinta datos inventados** (`year||2021`, `price||32500`, `market_price||38200`, `margin||18`, imagen Unsplash) que el backend no emite.
  - El **detalle de oportunidad** (fases/feedback) llama a endpoints que **no existen** en el router.
  - El flujo de búsqueda **síncrono nieto persiste nada**: el radar, las oportunidades y los KPIs quedan vacíos en el uso normal.
- El **mercado español** se basa en **fixtures sintéticos auto-registrados por defecto** que se persisten 6h en `cached_market` — decisiones de compra basadas en datos falsos.
- El repo contiene un **clon completo no trackeado** (`ai-business-platform-clone/`) con su propio `.git` apuntando al mismo origin, con trabajo no mergeado (`security_middleware.py`, `token_blacklist.py`).
- **Seguridad sin mínimos de producción**: sin CSRF, sin CSP, sin `TRUSTED_HOSTS`/HTTPS-enforce, vulnerabilidad ALTA `brace-expansion` en npm, una **Firebase API key hardcodeada y trackeada**.

**Veredicto global: 48/100** → el producto **NO es operable** para el objetivo para el que fue creado. Es una base backend prometedora con capa frontal parcial y móvil inacabada.

---

## 2) ARQUITECTURA ENCONTRADA

### Backend (FastAPI, Python 3.13)
- **Routers** (`app/api/v1/`): `auth`, `health`, `search`, `searches`, `search_orders`, `inspection`, `deals`, `vehicles`, `opportunities`, `dashboard`, `admin_*`, `notifications`, `mobile` (muerto), `users`, `api_keys`, `budget_search` + subcarpeta `routes/` con vista nueva (`health`, `inspection`, `search`, `vehicles`).
- **Servicios**: `auth_service`, `search_engine`, `search_orchestrator`, `search_persistence`, `opportunity_finder`, `profit_analyzer`, `evaluation_engine`, `negotiation_engine`, `vehicle_scorer`, `comparable_market_estimator`, `deal_service`, `inspection_service`.
- **Providers**: `autoscout24` DE y ES (REAL, scraping `__NEXT_DATA__` + fallback selectores HTML), `mobile_de` (REAL pero 403 sin proxy, desactivado), `es_market_fixture` y `coches_net_fixture` (MOCK).
- **Jobs**: scheduler en-proceso, `process_search_orders`, `provider_canary`, cleaners.
- **Repositorios** (`app/repositories/`) y **modelos** SQLAlchemy 2.0 tipados.

### Frontend (Next.js App Router + React Query + Axios)
- `frontend/src/app/services/api/client.ts` con retry/refresh.
- Pantallas: auth (login/register), dashboard, search, history, deals, opportunities, settings, `agents/workflows/approvals` (fantasma), layout móvil con `MobileTabBar`, tema violeta.

### Mobile (Capacitor 6 en frontend vs 8 en raíz)
- `frontend/android/` con deep links (`aibusiness://`), offline queue (IndexedDB), permisos Android declarados, biometría.
- **NO compila hoy.**

### Base de datos (PostgreSQL + Alembic)
- 25 migraciones lineales (head `n5o6p7q8r9s0`), backup/restore `pg_dump -Fc` + gpg AES256 + retención.

### Infra
- `Dockerfile` + `docker-compose.yml` (api, frontend, db, redis) + `docker-compose.obs.yml` (perfil obs), GitHub Actions (CI + mobile).

---

## 3) VERIFICACIÓN DE AFIRMACIONES CRÍTICAS (verificación propia del coordinador)

| # | Afirmación | Resultado | Evidencia |
|---|-----------|:---:|-----------|
| a | `opportunities/page.tsx` pinta datos inventados | ✔ | `frontend/src/app/(app)/opportunities/page.tsx:148-156` — `image \|\| unsplash…`, `year \|\| 2021`, `price \|\| 32500`, `market_price \|\| 38200`, `margin \|\| 18`, `status \|\| "active"`, `phase \|\| "Análisis de mercado"`, `agent \|\| "Analista de Mercado"` |
| b | `opportunities.py` solo expone lista/cursor/export-csv | ✔ | `app/api/v1/opportunities.py:120,158,181`; **no hay** `/{id}`, `PATCH /phases`, `POST /feedback`; la UI los llama (`useOpportunityDetail.ts:63,74,117`) |
| c | `VehicleDrawer`/`SimulateProfitPanel` usan `external_id` | ✔ | `VehicleDrawer.tsx:402` (createDeal), `:458`, `:349` (inspección), `:452` (simulador) → backend exige UUID interno (`vehicles.py:237`, `routes/inspection.py:74-79`) |
| d | `mobile.py` no montado | ✔ | `app/api/v1/router.py:11-53` no importa `mobile.py`; endpoint `/mobile/version` muerto |
| e | `network_security_config.xml` con merge conflict | ✔ | `frontend/android/app/src/main/res/xml/network_security_config.xml:5,30,33,39,53` — `<<<<<<< ours / ||||||| base / ======= / >>>>>>> theirs` + `REPLACE_WITH_REAL_PIN_1` |
| f | `search_engine.py` no persiste | ✔ | `app/services/search_engine.py:132-154` devuelve result en memoria; persistencia solo vía job (`search_persistence.py:41+`) |
| g | Head alembic real = `n5o6p7q8r9s0` | ✔ | `alembic/versions/n5o6p7q8r9s0_add_feature_flags_table.py:16-17` |
| h | README dice `g1h2i3j4k5l6` | ✔ | `README.md:81` — desactualizado |
| i | `tests/unit/test_search_engine.py` NO existe | ✔ | glob = 0 resultados |
| j | `service-worker.js` existe pero no se registra | ✔ | `frontend/public/service-worker.js` existe; `use-service-worker.ts:18-19` registra pero el hook es huérfano (grep no encuentra import) |
| k | `ai-business-platform-clone/` duplicado no trackeado | ✔ | `git status` → `?? ai-business-platform-clone/`; `.git` propio; HEAD = `e2ba913`; mismo origin |
| + | Capacitor 6 vs 8 | ✔ | `frontend/package.json` → `@capacitor/*@^6.2.1`; `package.json` raíz → `^8.4.2` |
| + | Dockerfile instala dev-deps en prod | ✔ | `Dockerfile:16` → `uv sync --locked --group dev` |
| + | Firebase API key hardcodeada | ✔ | `frontend/src/app/services/analytics.ts:19-22` |
| + | Campana sin onClick | ✔ | `frontend/src/app/layout/navbar.tsx:34` |
| + | `search/page.tsx` no lee `useSearchParams` | ✔ | `frontend/src/app/(app)/search/page.tsx:3` — solo `useState` |
| + | Fixtures ES auto-registrados por perfil | ✔ | `app/providers/registry.py:86-92,113-117` (perfil SPAIN por defecto) |
| + | mobile_de: default False / `.env.example`=true | ✔ | `config.py:215` vs `.env.example:137`; además `process_search_orders.py:261-268` fuerza `"mobile_de"` en defaults |
| ⚠️ | Marcas/modelos estáticos en `search.ts:84-103` | ⚠️ | El archivo referenciado por A2 **no existe** en la ubicación citada; `SearchFilters.tsx:105-130` usa campos de texto libre |

**Resumen: 20 verificaciones → 19 ✔ · 1 ⚠️ · 0 ✘**

---

## 4) CONTRADICCIONES ENTRE AGENTES (y resolución)

| Contradicción | Agentes | Resolución (con evidencia) |
|---|---|---|
| "Backend completo, sin mocks, todo OK" vs "flujos rotos y datos mock" | A1 vs A8/A9/A12 | A1 describió existencia de módulos (cierto: routers delegan en servicios); A8/9/12 verificaron **la cadena operacional completa** y tenían razón: contratos UI↔API rotos (`VehicleDrawer.tsx:402/349/452` vs `vehicles.py:237`), búsqueda síncrona sin persistir (`search_engine.py:132-154`), fixtures ES activos por defecto (`registry.py:86-92`). **Resolución: A8/A9/A12 correctos; el "sin mocks" de A1 es falso a nivel de proveedores.**
| PWA "parcial (archivo en public/)" vs "no registrada" | A2 vs A12 | El archivo existe pero `use-service-worker.ts` es un hook huérfano (nunca importado) y no hay `manifest.json`. **Resolución: A12 correcto; funcionalmente la PWA es inexistente.**
| Head alembic en README vs head real | A11 vs A4 | `README.md:81` dice `g1h2i3j4k5l6`; real `n5o6p7q8r9s0`. **Resolución: README desactualizado.**
| `mobile.py` "implementado" vs "no montado" | A1 (docstring) vs A11 | Endpoint definido (`mobile.py:35`) pero no importado en `router.py`. **Resolución: endpoint muerto.**
| mobile_de "default desactivado" vs `.env.example=true` | A9 vs config | Real: `config.py:215`=False, `.env.example:137`=true, compose=false y el job fuerza `"mobile_de"`. **Resolución: incoherencia de config real + bug en job.**
| README afirma network_security_config release OK | A11 vs A3 | Verificado: 5 líneas con marcadores de merge. **Resolución: A3 correcto, claim README refutado.**
| `test_search_engine.py` faltante | A1 vs A6/A10 | Glob confirma que no existe. **Resolución: ambos coinciden (A6 lo cuantifica: solo existe en integración y allí falla).** |

---

## 5) PUNTUACIÓN POR ÁREA (ponderada)

| Área | Peso | Nota | Justificación (1 línea) |
|---|---:|---:|---|
| Backend | 15% | 55 | Arquitectura real, 1.348 unit OK, pero flujos clave rotos (500/404 por `external_id`), búsqueda síncrona sin persistir y 22 tests de integración fallando fuera de CI. |
| Frontend | 15% | 52 | App web funciona (auth, dashboard, search reales) pero con UI fantasma / datos inventados, acciones muertas y PWA inexistente. |
| Mobile | 10% | 12 | **NO compila**: merge conflict en XML, sin `.env.local` (build aborta), node_modules ausente, Capacitor 6 vs 8, sin `google-services.json`. Solo deep links/offline en código. |
| Base de datos | 10% | 70 | 25 migraciones lineales OK, backup/restore+gpg funcionales, compose verificado; deuda: `vehicle.equipment` sin migrar a JSON, `cached_market` sin índices, tipos legacy. |
| Seguridad | 10% | 45 | JWT+Argon2+rate limit buenos, pero sin CSRF/CSP/TRUSTED_HOSTS/HTTPS-enforce, vuln ALTA `brace-expansion`, Firebase key trackeada, email en logs. |
| Testing/QA | 10% | 55 | 1.348 unit 100% OK (cobertura 98% módulos críticos, 79% global), pero 22 integración fallan **fuera** del subset de CI (verdes por exclusión), sin E2E real, vitest threshold 30% y no ejecutable localmente (sin node_modules). |
| DevOps | 10% | 50 | Compose verificado en vivo (build, migraciones, health 200, frontend sirve HTML), pero dev-deps en prod, root, puertos hardcodeados, sin CD, `/metrics` ausente, smoke móvil cosmético, sin rollback. |
| Funcionalidad de negocio | 15% | 42 | Flujo core (oportunidades→deal→simulación→inspección→persistencia) **roto o inventado** end-to-end; el motor de búsqueda/análisis sí funciona. |
| Integraciones externas | 5% | 40 | AutoScout24 DE/ES reales y funcionando; mobile.de 403 bloqueado; **mercado ES = fixtures falsos** persistidos 6h en cache; sin respeto a `Retry-After`. |

---

## 6) PORCENTAJE GLOBAL

```
0,15 × 55 =  8,25   (Backend)
0,15 × 52 =  7,80   (Frontend)
0,10 × 12 =  1,20   (Mobile)
0,10 × 70 =  7,00   (Base de datos)
0,10 × 45 =  4,50   (Seguridad)
0,10 × 55 =  5,50   (Testing/QA)
0,10 × 50 =  5,00   (DevOps)
0,15 × 42 =  6,30   (Funcionalidad de negocio)
0,05 × 40 =  2,00   (Integraciones externas)
─────────────────────────────
TOTAL        = 47,55 → 48/100
```

**Completitud global: 48% · Falta: 52%**

Coherencia interna: el producto no es operable (producto 42/100) → funcionalidad de negocio 42 (<50 ✔); mobile 12 (no compila); frontend 52 (funciona con UI fantasma). El 48 global es coherente con un backend sustancial pero con el ciclo completo de negocio no desplegable.

---

## 7) ESTADO FUNCIONAL POR FEATURE

### ✅ COMPLETAS
| Feature | Evidencia |
|---|---|
| Autenticación JWT + refresh + API keys (Argon2) | `app/api/v1/auth.py`, `app/services/auth_service.py`; unit 100% |
| Motor búsqueda + análisis en memoria (providers→score→mercado→profit→oportunidad) | `search_engine.py:132-154`, orquestador |
| Gestión de deals (listado y transiciones de estado) | `app/api/v1/deals.py`, `app/services/deal/pipeline.py` |
| Dashboard con KPIs calculados de BD | `app/api/v1/dashboard.py`; `dashboard/page.tsx:133-163` |
| Scheduler + persistencia vía jobs de órdenes background | `app/jobs/scheduler.py`, `process_search_orders.py` |
| Migraciones + backup/restore | 25 migraciones lineales; `scripts/backup_postgres.sh`, `restore_postgres.sh` |
| Frontend: API client con retry/refresh, auth guard, dashboard | `frontend/src/app/services/api/client.ts` |
| Deep links y offline queue (código mobile, no integrado) | `use-deep-links.ts`, `offline-queue.ts` |
| AutoScout24 DE/ES en vivo | `app/providers/autoscout24.py`, `autoscout24_es.py`; verificado en vivo |
| Health compuesto (api/database/redis) con semántica correcta | `app/api/v1/routes/health.py`; tests 5 estados |

### 🟡 PARCIALES
| Feature | Qué falta |
|---|---|
| Búsqueda persistente | Solo vía job background; el flujo síncrono **no persiste** |
| Oportunidades (backend) | API lista/cursor/CSV funciona; la UI no las muestra (pinta defaults) |
| PWA | `service-worker.js` existe pero no registrado; sin `manifest.json` |
| Integración (pruebas) | 225 pasan, 22 fallan — fuera del subset que corre CI |
| Historial | Listar/borrar OK; "repetir búsqueda" no funciona (params ignorados) |

### 🟠 MOCK
| Feature | Evidencia |
|---|---|
| Mercado España | `es_market_fixture` + `coches_net_fixture` auto-registrados por perfil SPAIN (`registry.py:86-99,113-125`) y persistidos en `cached_market` 6h |
| Pantalla Oportunidades | Datos inventados en UI (`opportunities/page.tsx:148-156`) |
| Detalle de oportunidad | UI fantasma que llama endpoints inexistentes |
| Pantallas `/agents` `/workflows` `/approvals` | Datos fabricados + hooks a endpoints inexistentes (`useAgents.ts:16`, `useWorkflows.ts:15`, `useApprovals.ts:18`) |

### 🔴 ROTAS
| Bug | Evidencia |
|---|---|
| Crear deal → **500** (external_id como vehicle_id, viola FK UUID) | `VehicleDrawer.tsx:402,458` → `deals.vehicle_id` (Uuid, FK) |
| Simular beneficio e iniciar inspección → **404** | `VehicleDrawer.tsx:349,452` → `vehicles.py:237`, `routes/inspection.py:74-79` |
| Deep links de push: `router` sin importar | `push-notifications.ts` |
| "Repetir búsqueda" desde historial | `history/page.tsx` → `/search?query=…`; `search/page.tsx` no lee params |
| Búsqueda síncrona no persiste → radar/oportunidades/KPIs vacíos | `search_engine.py:132-154` |
| **Build Android roto** | merge conflict en `network_security_config.xml`, `.env.local` ausente |
| `ProcessSearchOrdersJob` fuerza `mobile_de` desactivado → ProviderIssue | `process_search_orders.py:261-268` |
| Google login por defecto | requiere Firebase service account no configurada |
| `app/api/v1/mobile.py` prometido y no montado | `router.py:11-53` |

### ⚫ NO IMPLEMENTADAS
Favoritos/watchlist · Centro de notificaciones web · `GET /opportunities/{id}` + fases/feedback · endpoint `/mobile/version` operativo · CD/despliegue automatizado · E2E automatizado (Playwright) · coches.net **live** (solo fixtures) · street_auto_center/auto_speed · CSP/CSRF/TRUSTED_HOSTS/HTTPS-enforce · `/metrics` Prometheus.

---

## 8) RIESGOS

| Riesgo | Severidad | Evidencia |
|---|---|---|
| Datos falsos persisten como "mercado" en prod (fixtures ES, TTL 6h) | 🔴 CRÍTICO | `registry.py:86-99`; `cached_market` |
| App Android no compila → sin entregable móvil | 🔴 CRÍTICO | `network_security_config.xml:5-53` |
| Clon duplicado del repo con trabajo no mergeado | 🔴 CRÍTICO | `?? ai-business-platform-clone/` (HEAD `e2ba913`); `security_middleware.py`, `token_blacklist.py` sin mergear |
| Contratos UI↔API rotos (500/404 en flujo core) | 🔴 CRÍTICO | `VehicleDrawer.tsx:402/349/452` |
| Oportunidad/Datos inventados presentados como reales | 🟠 ALTO | `opportunities/page.tsx:148-156` — riesgo de decisión de compra con números falsos |
| Seguridad baja: sin CSRF/CSP/HTTPS/TRUSTED_HOSTS | 🟠 ALTO | verificación Agente 5 + `router.py` |
| Vulnerabilidad ALTA `brace-expansion` | 🟠 ALTO | `npm audit` |
| Firebase API key trackeada en repo | 🟠 ALTO | `analytics.ts:22` |
| Tests "verdes por exclusión" (22 fails fuera de CI) | 🟠 ALTO | Agente 6 |
| `.env.local` sin crear aborta build móvil | 🟠 ALTO | `check-capacitor-config.mjs` |
| Versiones Capacitor 6 vs 8 | 🟠 ALTO | `frontend/package.json` vs `package.json` raíz |
| Docker: dev-deps en imagen prod, root, bind-mount | 🟠 ALTO | `Dockerfile:16` |
| Modelo económicos con `print()` residuales y lógica en routers | 🟡 MEDIO | `negotiation_engine.py:68`, `opportunity_finder.py:139`, `profit_analyzer.py:222`, etc. |
| KPI "Beneficio est." suma oportunidades sin filtrar | 🟡 MEDIO | `dashboard/page.tsx:141-144` |

---

## 9) LISTA COMPLETA DE TASKS

### BLOQUE 1 — BACKEND

**TASK BC-B-001 — Crear deal devuelve 500 por misuso de `external_id`**
- **Problema:** `VehicleDrawer.tsx:402,458` envía `vehicle_id: vehicle.external_id` (id del anuncio, ej. `"579031"`) pero `deals.vehicle_id` es `sa.Uuid` con FK → violación de integridad → 500.
- **Objetivo:** que `POST /deals` acepte y resuelva `external_id` al `Vehicle.id` interno (o el frontend use el UUID interno del vehículo persistido).
- **Archivos afectados:** `app/api/v1/deals.py`, `VehicleDrawer.tsx`, `app/services/deal/pipeline.py`
- **Resultado esperado:** crear un deal desde un resultado de búsqueda responde 201 y aparece en el listado.
- **Criterio de aceptación:** smoke manual: búsqueda → crear deal → 201 + fila correcta con FK válida; sin 500.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna.

**TASK BC-B-002 — Simular beneficio e iniciar inspección devuelven 404**
- **Problema:** `SimulateProfitPanel.tsx:452` → `POST /vehicles/{external_id}/simulate-profit` y `VehicleDrawer.tsx:349` → `/inspection/?vehicle_id=external_id`. El backend exige un vehículo del usuario por UUID interno (`vehicles.py:237 _get_owned_vehicle`, `routes/inspection.py:74-79`) → 404.
- **Objetivo:** resolver `external_id → UUID` antes de las llamadas, o persistir el vehículo y usar su id real; exponer el UUID en la UI si hace falta.
- **Archivos afectados:** `app/api/v1/vehicles.py`, `app/api/v1/routes/inspection.py`, `SimulateProfitPanel.tsx`, `VehicleDrawer.tsx`
- **Resultado esperado:** simular beneficio (200) e iniciar inspección (201) desde cualquier vehículo de búsqueda en vivo.
- **Criterio de aceptación:** smoke: búsqueda → simular → 200 con breakdown; inspección → 201.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-001 (si se centraliza la resolución de IDs).

**TASK BC-B-003 — La búsqueda síncrona no persiste nada**
- **Problema:** `search_engine.py:132-154` solo devuelve resultados en memoria; la persistencia vive en el job background (`search_persistence.py:41+`, `process_search_orders.py`). Radar, oportunidades y KPIs quedan en 0 tras uso normal.
- **Objetivo:** persistir vehículos + oportunidades + búsqueda en el flujo síncrono reutilizando `search_persistence.py`.
- **Archivos afectados:** `app/services/search_engine.py`, `app/api/v1/routes/search.py`, `app/services/search_persistence.py`
- **Resultado esperado:** tras una búsqueda síncrona existen filas en `vehicles`, `opportunities`, `searches`.
- **Criterio de aceptación:** búsqueda síncrona → `GET /vehicles` y `/opportunities` devuelven los resultados; KPIs del dashboard > 0.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna.

**TASK BC-B-004 — Endpoint `/api/v1/mobile/version` muerto**
- **Problema:** `app/api/v1/mobile.py:32-51` define el router pero `router.py:11-53` no lo importa → 404 prometido en docstring.
- **Objetivo:** montar el router o eliminar el módulo muerto.
- **Archivos afectados:** `app/api/v1/router.py`, `app/api/v1/mobile.py`
- **Criterio de aceptación:** `GET /api/v1/mobile/version` → 200, o el módulo desaparece.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK BC-B-005 — Filtro `status` ignorado en oportunidades**
- **Problema:** la UI envía `status` pero `list_opportunities` lo descarta silenciosamente; el contrato es `recommendation/min_score/min_roi/limit/offset`.
- **Objetivo:** alinear filtro UI↔API.
- **Archivos afectados:** `app/api/v1/opportunities.py`, `frontend/src/app/services/opportunities.ts`
- **Criterio de aceptación:** filtrar Activas/Pendientes cambia la lista.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** BC-B-006 (si se rediseña el contrato).

**TASK BC-B-006 — Rutas de detalle de oportunidad inexistentes**
- **Problema:** la UI llama `GET /opportunities/{id}`, `PATCH /opportunities/{id}/phases/{phaseId}`, `POST .../feedback` (`useOpportunityDetail.ts:63,74,117`); el backend solo tiene lista/cursor/export-csv.
- **Objetivo:** implementar las rutas O eliminar la UI fantasma.
- **Archivos afectados:** `app/api/v1/opportunities.py`, `frontend/src/app/hooks/useOpportunityDetail.ts`, páginas de oportunidad
- **Criterio de aceptación:** contrato 1:1 entre la UI y la API; detalle devuelve datos reales.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK BC-B-007 — `print()` residuales en servicios críticos**
- **Problema:** `print()` en `negotiation_engine.py:68`, `opportunity_finder.py:139`, `profit_analyzer.py:222`, `search_engine.py:61`, `vehicle_scorer.py:173`.
- **Objetivo:** sustituir por `logging`.
- **Criterio de aceptación:** sin `print()` en `app/services/` (grep 0).
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK BC-B-008 — No se respeta `Retry-After` en 429**
- **Problema:** `ProviderRateLimitError.retry_after` se captura pero nadie lo respeta.
- **Objetivo:** respetar `Retry-After` en `ProviderHttpClient` / orquestador.
- **Archivos afectados:** `app/providers/http_client.py`, `app/providers/exceptions.py`, `app/services/search_orchestrator.py`
- **Criterio de aceptación:** tras 429, la siguiente petición espera `retry_after`.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK BC-B-009 — Normalización naive de marca/modelo**
- **Problema:** `_split_brand_model` (`providers/base.py:458-474`) toma la primera palabra como marca, sin tabla de marcas/modelos.
- **Objetivo:** introducir mapping de marcas/modelos para AS24/mobile.de/ES.
- **Criterio de aceptación:** `brand` y `model` correctos para un set de fixtures conocido.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK BC-B-010 — Job fuerza `mobile_de` desactivado**
- **Problema:** `process_search_orders.py:261-268` fuerza `"mobile_de"` en los defaults incluso con `enable_mobile_de=False` → ProviderIssue en cada orden.
- **Objetivo:** usar `_default_search_providers` coherente con config.
- **Criterio de aceptación:** sin ProviderIssue "not registered" por defecto.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** P3 (coherencia de config) para consistencia.

**TASK BC-B-011 — Arreglar los 22 fallos de integración y cubrir el motor**
- **Problema:** 225 integración pasan, 22 fallan — todos **fuera** del subset INT.1 de CI ("verdes por exclusión"). Incluye `test_password_reset_api` (404 real del token), `test_search_engine` (assert 1==2), `test_vehicle_api` (500 esperado vs 401), `test_security_api`.
- **Objetivo:** corregir los bugs revelados y añadir todo el set a CI. Crear `tests/unit/test_search_engine.py`.
- **Criterio de aceptación:** `pytest tests/unit tests/integration` → 0 failed; CI ejecuta el set completo.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna (es diagnóstico + fix).

### BLOQUE 2 — FRONTEND

**TASK FE-F-001 — Eliminar los fallbacks inventados en Oportunidades**
- **Problema:** `opportunities/page.tsx:148-156` inventa `year 2021`, `price 32500`, `market_price 38200`, `margin 18`, `status active`, `phase`, `agent`, imagen Unsplash cuando el backend no los emite.
- **Objetivo:** renderizar SOLO campos reales del contrato (`OpportunityRead`) y diseñar empty/loading states reales.
- **Criterio de aceptación:** la pantalla no muestra ni un campo que el backend no devuelva; grep de `|| 2021` / `|| 32500` = 0.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-006 (contrato de detalle).

**TASK FE-F-002 — Acciones muertas en Oportunidades**
- **Problema:** botón "Nueva oportunidad" sin `onClick` (`page.tsx:63`); empty-state enlaza a `/opportunities/new` inexistente (404); filtro de estado descartado.
- **Objetivo:** quitar el botón muerto, arreglar el empty-state o crear la ruta real.
- **Criterio de aceptación:** ninguna acción visible redirige a 404 ni hace nada.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** FE-F-001, BC-B-006.

**TASK FE-F-003 — "Repetir búsqueda" desde historial no funciona**
- **Problema:** `history/page.tsx:21-24` → `/search?query=...` pero `search/page.tsx` no lee `useSearchParams`.
- **Objetivo:** hidratar el formulario con los params.
- **Criterio de aceptación:** pulsar repetir búsqueda rellena y ejecuta la búsqueda.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK FE-F-004 — PWA / offline**
- **Problema:** `service-worker.js` existe pero `use-service-worker.ts` nunca se importa; `use-offline` no exponen cache funcional; sin `manifest.json`.
- **Objetivo:** registrar el SW, añadir manifest, configurar estrategias de cache.
- **Criterio de aceptación:** Lighthouse PWA instalable; offline muestra caché de búsquedas.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK FE-F-005 — Campana de notificaciones**
- **Problema:** `navbar.tsx:34` botón sin `onClick`; `initPushNotifications()` nunca se llama.
- **Objetivo:** implementar o quitar; conectar con M5/M6.
- **Criterio de aceptación:** la campana acciona una acción real o se elimina.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** MO-M-006 (si se conecta push).

**TASK FE-F-006 — Pantallas /agents /workflows /approvals**
- **Problema:** `useAgents.ts:16`, `useWorkflows.ts:15`, `useApprovals.ts:18` llaman a endpoints inexistentes y muestran datos fabricados (Fechas "Hace 15 min", `analisis_*.pdf`).
- **Objetivo:** implementar las APIs o retirar las pantallas de la navegación.
- **Criterio de aceptación:** ninguna pantalla navegable muestra datos falsos ni error permanente.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK FE-F-007 — KPI "Beneficio est." engañoso**
- **Problema:** `dashboard/page.tsx:141-144` suma `estimated_profit` de todas sin filtrar negativas ni recomendación.
- **Objetivo:** filtrar por `estimated_profit > 0` o recomendación activa; documentar el criterio.
- **Criterio de aceptación:** el KPI solo suma oportunidades viables.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** BC-B-003 (persistencia).

**TASK FE-F-008 — Marcas/modelos dinámicos**
- **Problema:** filtros usan texto libre/lista no respaldada por el backend.
- **Objetivo:** endpoint `GET /meta/brands` o autocompletado desde datos escrapeados.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** BC-B-009.

**TASK FE-F-009 — Subir umbrales de vitest**
- **Problema:** `vitest.config.ts:15-32` thresholds 30% lines / 20% branches.
- **Objetivo:** subir a ≥70% y ampliar casos de UI.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** instalar `frontend/node_modules` en CI/local.

**TASK FE-F-010 — Accesibilidad**
- **Problema:** `navbar.tsx:34` sin aria-label; errores sin `aria-live`; skeletons sin `aria-busy`; pagination sin aria-label.
- **Objetivo:** cumplir WCAG AA básico en los flujos principales.
- **Prioridad:** 🟢 BAJA
- **Dependencias:** ninguna.

### BLOQUE 3 — MOBILE / ANDROID

**TASK MO-M-001 — Resolver merge conflict en `network_security_config.xml`**
- **Problema:** `frontend/android/app/src/main/res/xml/network_security_config.xml:5-53` contiene `<<<<<<< ours / ||||||| base / ======= / >>>>>>> theirs` + `REPLACE_WITH_REAL_PIN_1` → XML inválido, build roto.
- **Objetivo:** producción: pinning de CA para `10.0.2.2`/`localhost`, cleartext bloqueado para el resto.
- **Criterio de aceptación:** `gradlew assembleDebug` y `assembleRelease` compilan; release no permite cleartext fuera del emulador.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna.

**TASK MO-M-002 — `.env.local` de frontend inexistente**
- **Problema:** `check-capacitor-config.mjs` aborta (exit 1) sin `NEXT_PUBLIC_API_URL` / Google client IDs → build falla al inicio.
- **Objetivo:** documentar + crear `.env.local` mínimo o hacer el check no abortivo con defaults doc.
- **Criterio de aceptación:** `npm run cap:build:android` pasa el check.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna.

**TASK MO-M-003 — Versiones Capacitor inconsistentes**
- **Problema:** `frontend/package.json` usa `@capacitor/*@^6.2.1`; `package.json` raíz `^8.4.2`.
- **Objetivo:** una sola versión (definir 6 o 8) en `frontend/`.
- **Criterio de aceptación:** lockfile unificado y build reproducido.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** MO-M-004.

**TASK MO-M-004 — Compilar el APK de verdad**
- **Problema:** no hay `frontend/node_modules`; no se puede ejecutar `npm run export` + `cap sync` + `gradlew`.
- **Objetivo:** `npm ci` → `npm run build` → `npx cap sync android` → `gradlew.bat assembleDebug` produce APK instalable.
- **Criterio de aceptación:** APK debug firmado generado y verificable (`verify_android_build.sh`).
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** MO-M-001, MO-M-002, MO-M-003.

**TASK MO-M-005 — Push notifications / FCM**
- **Problema:** `google-services.json` ausente → FCM no funciona; manifest lo exige.
- **Objetivo:** configurar Firebase, generar `google-services.json`, habilitar push en Android.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** MO-M-004.

**TASK MO-M-006 — Inicializar push/deep links/navegación**
- **Problema:** `initPushNotifications()` nunca se llama; `NotificationNavigator` y `useDeepLinks` son huérfanos; `router` sin importar en `push-notifications.ts`.
- **Objetivo:** inicializar en el arranque y conectar navegación.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** MO-M-005.

**TASK MO-M-007 — Smoke móvil real**
- **Problema:** el smoke CI `mobile-smoke-tests.yml` es cosmético: el `grep fatal` usa `|| true` y nunca falla el job.
- **Objetivo:** asserts reales (proceso vivo, pantalla home cargada, sin crash tras N segundos).
- **Prioridad:** 🟢 BAJA
- **Dependencias:** MO-M-004.

### BLOQUE 4 — BASE DE DATOS

**TASK DB-D-001 — Migrar `vehicle.equipment` a JSON**
- **Problema:** `vehicle.py:69-70` `equipment` sigue `Text`; `images` ya se migró a JSON (`k3l4m5n6o7p8`).
- **Objetivo:** migración nueva a JSONColumn manteniendo lecturas compatibles.
- **Criterio de aceptación:** `alembic upgrade head` sobre Postgres limpio + datos legacy migrados.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK DB-D-002 — Índices en `cached_market`**
- **Problema:** sin índices explícitos para búsqueda por `market_hash`/`expires_at`.
- **Criterio de aceptación:** EXPLAIN muestra index scan en las consultas del repo.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK DB-D-003 — Normalizar tipos `String(36)` → `Uuid`**
- **Problema:** `audit_log.py:17`, `api_key.py:19`, `refresh_token.py:19`, `push_token.py:19`, `password_reset_token.py:15`, `verification_token.py:15`.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** pruebacón con migración nueva.

**TASK DB-D-004 — Tests de DB sobre Postgres real**
- **Problema:** tests de repos usan sqlite+aiosqlite (diferente a prod).
- **Objetivo:** suite de integración DB sobre Postgres 16 en CI.
- **Prioridad:** 🟢 BAJA
- **Dependencias:** —.

### BLOQUE 5 — SEGURIDAD

**TASK SE-S-001 — Estrategia de tokens / CSRF**
- **Problema:** JWT en `localStorage`, sin CSRF, sin cookies `HttpOnly`.
- **Objetivo:** decidir modelo (cookies HttpOnly + CSRF, o tokens en memoria) e implementar.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna.

**TASK SE-S-002 — Cabeceras CSP + security middleware**
- **Problema:** sin CSP; `security_middleware.py` existe solo en el clon.
- **Objetivo:** portar al raíz + headers `Content-Security-Policy`, `X-Content-Type-Options`, etc.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** R-A1 (integrar clon).

**TASK SE-S-003 — `TRUSTED_HOSTS` + HTTPS-enforce**
- **Objetivo:** validar Host en prod y redirigir/negar HTTP.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK SE-S-004 — `npm audit` vuln ALTA `brace-expansion`**
- **Objetivo:** `npm audit fix` / upgrade de la dependencia; re-scannear.
- **Criterio de aceptación:** `npm audit` → 0 high.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** permitir `npm install` en frontend.

**TASK SE-S-005 — Firebase API key hardcodeada**
- **Problema:** `analytics.ts:22` contiene key real.
- **Objetivo:** env-only + rotar la key comprometida (es pública por diseño Firebase web, pero no debe ir en repo hardcodeada).
- **Criterio de aceptación:** sin secretos en código (grep de `AIzaSy` = 0).
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK SE-S-006 — No guardar email en logs de login fallido**
- **Problema:** `audit_service.py:67` registra `login_failed` con email.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

### BLOQUE 6 — DEVOPS / PRODUCCIÓN

**TASK DV-V-001 — Imagen Docker productiva limpia**
- **Problema:** `Dockerfile:16` instala `--group dev` en prod; corre como root; bind-mount host en runtime.
- **Objetivo:** etapa build sin dev-deps, `USER` no-root, copia de artefactos sin mount.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK DV-V-002 — Puertos y `.env` para compose**
- **Problema:** puertos hardcodeados (`5432/6379/8000/3000`) chocan con otros stacks; sin `.env` la API crash-loops por JWT vacío.
- **Objetivo:** puertos por variable y guard-friendly arranque (fail fast con mensaje claro).
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK DV-V-003 — CD backend/frontend**
- **Objetivo:** pipeline de despliegue (build + push imagen + deploy) tras CI.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** DV-V-001.

**TASK DV-V-004 — Observabilidad real**
- **Problema:** profile `obs` monta Prometheus sin `prometheus.yml` (no scrapea la API); `/metrics` no existe.
- **Objetivo:** endpoint `/metrics` + config de scraping + dashboards Grafana provisionados.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** ninguna.

**TASK DV-V-005 — Healthcheck frontend en compose**
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** —.

**TASK DV-V-006 — CI de integración completa**
- **Problema:** CI solo corre subset INT.1; los 22 fallos pasan desapercibidos.
- **Objetivo:** correr el set completo de integración.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-011.

**TASK DV-V-007 — Runbook de rollback**
- **Objetivo:** documentar rollback de versión, `alembic downgrade`, restore de backup.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** —.

**TASK DV-V-008 — `pg_dump` disponible / documentar dependencia**
- **Problema:** los scripts de backup exigen `pg_dump` en el host; la imagen no lo incluye.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** —.

### BLOQUE 7 — PROVEEDORES / DATOS EXTERNOS

**TASK PV-P-001 — Desactivar fixtures ES por defecto**
- **Problema:** `es_market_fixture` y `coches_net_fixture` auto-registrados con perfil SPAIN (`registry.py:86-125`) — el "mercado ES" son datos sintéticos.
- **Objetivo:** exigir flag explícito (o marcar `source: synthetic` para que el estimador nunca los use como verdad).
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-003 (para que AS24-ES llene el hueco).

**TASK PV-P-002 — Purgar `cached_market` contaminado**
- **Problema:** estimaciones basadas en fixtures persistidas 6h.
- **Objetivo:** limpiar entradas de fuentes sintéticas.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** PV-P-001.

**TASK PV-P-003 — Coherencia `ENABLE_MOBILE_DE`**
- **Problema:** `config.py:215`=False vs `.env.example:137`=True vs compose=false vs job que lo fuerza.
- **Objetivo:** una sola fuente de verdad + docs.
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** BC-B-010.

**TASK PV-P-004 — Política de reintentos unificada (Retry-After)**
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** BC-B-008.

### BLOQUE 8 — PRODUCTO / UX

**TASK PR-U-001 — Detalle de oportunidad real**
- **Problema:** la pantalla de detalle llama endpoints inexistentes y muestra fases/agentes/archivos fabricados.
- **Objetivo:** implementar el detalle con datos reales (con BC-B-006) o deshabilitar.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-006, FE-F-001.

**TASK PR-U-002 — Flujo crear deal end-to-end**
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-001.

**TASK PR-U-003 — Flujo simular beneficio / inspección end-to-end**
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** BC-B-002.

**TASK PR-U-004 — Poblar radar/oportunidades/KPIs con datos reales**
- **Prioridad:** 🟠 ALTA
- **Dependencias:** BC-B-003, FE-F-001.

**TASK PR-U-005 — Favoritos / watchlist**
- **Problema:** no existe en ninguna capa (solo mencionado en offline queue / service worker `sync-favorites`).
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** BC-B-003.

**TASK PR-U-006 — Centro de notificaciones web**
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** MO-M-006 / FE-F-005.

**TASK PR-U-007 — Google login operativo o desactivado**
- **Problema:** requiere Firebase service account; por defecto 401.
- **Prioridad:** 🟢 BAJA
- **Dependencias:** SE-S-005.

### BLOQUE 9 — DOCUMENTACIÓN

**TASK DO-D-001 — Actualizar head alembic en README**
- **Problema:** `README.md:81` dice `g1h2i3j4k5l6`; real `n5o6p7q8r9s0`.
- **Prioridad:** 🟢 BAJA

**TASK DO-D-002 — Completar `.env.example`**
- **Problema:** faltan `GEMINI_*`, `OPENAI_*`, `SEARCH_ORDER_*`, `JWT_PREVIOUS_SECRETS`, `LOG_*`, `PROVIDER_HTTP_MAX_HTML_BYTES`, `ENABLE_COCHES_NET_HTML_FIXTURE`; `ENABLE_MOBILE_DE` incorrecto.
- **Prioridad:** 🟢 BAJA

**TASK DO-D-003 — `CONTEXT_PERSONAL_USE`: `local@localhost` → `local@example.com`**
- **Prioridad:** 🟢 BAJA

**TASK DO-D-004 — Eliminar claims falsos**
- **Problema:** docs dicen que `/mobile/version` existe, que network_security_config release está bien, y el clon dice `/metrics`+monitoring implementados.
- **Prioridad:** 🟢 BAJA

### BLOQUE 10 — REPOSITORIO / ARQUITECTURA

**TASK AR-A-001 — Eliminar/archivar el clon duplicado**
- **Problema:** `ai-business-platform-clone/` con `.git` propio, mismo origin, trabajo no mergeado (`security_middleware.py`, `token_blacklist.py`, docs `deployment.md`, `CHANGELOG.md`, `.env.staging.example`, `.env.production.example`) y un `.env` real con credenciales.
- **Objetivo:** un solo árbol; integrar lo útil (seguridad middleware, token_blacklist, docs prod) al raíz.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** revisión manual del trabajo sin mergear.

**TASK AR-A-002 — Fusionar routers duplicados**
- **Problema:** `vehicles.py` + `routes/vehicles.py`; `searches.py` + `routes/search.py`, ambos registrados (`router.py:25-49`), mismos tags.
- **Objetivo:** un router por recurso; plan de deprecación.
- **Prioridad:** 🔴 CRÍTICA
- **Dependencias:** ninguna (riesgo de breaking; requiere cobertura).

**TASK AR-A-003 — Unificar schemas**
- **Problema:** `app/schemas/` vs `app/api/v1/schemas/` duplican entidades.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** AR-A-002.

**TASK AR-A-004 — Eliminar `fix.bat`/`fix.js`**
- **Problema:** código JS comiteado como parches one-shot.
- **Prioridad:** 🟠 ALTA
- **Dependencias:** ninguna.

**TASK AR-A-005 — Corregir violación de capas (routers → repos directos)**
- **Prioridad:** 🟡 MEDIA
- **Dependencias:** AR-A-002.

---

## 10) ROADMAP

### 🔴 BLOQUE A — NECESARIO PARA LA FUNCIONALIDAD
`BC-B-001` (deal 500) · `BC-B-002` (simular/inspección 404) · `BC-B-003` (persistencia síncrona) · `BC-B-006` (detalle oportunidad/fases) · `FE-F-001` (quitar datos inventados) · `FE-F-002` (acciones muertas) · `FE-F-003` (repetir búsqueda) · `PR-U-001/002/003/004` (flujos end-to-end) · `PV-P-001` (desactivar fixtures ES) · `MO-M-001/002/003/004` (que el móvil compile) · `AR-A-001/002` (un solo árbol y router) · `AR-A-003` (schemas).

### 🟠 BLOQUE B — NECESARIO PARA PRODUCCIÓN
`SE-S-001` (CSRF/tokens) · `SE-S-003` (TRUSTED_HOSTS/HTTPS) · `SE-S-004` (npm audit) · `SE-S-005` (Firebase key) · `DV-V-001/002` (imagen prod limpia, compose) · `DV-V-006`/`BC-B-011` (CI íntegra) · `DV-V-003/004/005/007/008` (CD, observabilidad, rollback) · `DB-D-001/002` (equipment JSON, índices) · `PV-P-002` (purgar cache) · `MO-M-005/006` (FCM, push) · `BC-B-008/010` (retry, job mobile_de) · `FE-F-006/007/008`.

### 🟢 BLOQUE C — MEJORAS
`SE-S-002/006` · `FE-F-004/005/009/010` · `MO-M-007` · `DB-D-003/004` · `PV-P-003/004` · `PR-U-005/006/007` · `F4-F10` · `DO-D-001..004` · `AR-A-004/005` · `BC-B-004/005/007/009`.

---

## 11) ESTADO REAL DEL PROYECTO

| Métrica | Valor |
|---|---|
| **Completitud estimada** | **48%** |
| **Falta aproximadamente** | **52%** |
| Tareas críticas pendientes | 18 |
| Tareas altas | 16 |
| Tareas medias | 23 |
| Tareas bajas | 8 |
| **Total tareas** | **65** |

**¿Por qué exactamente 48%?** Porque las áreas con masa crítica puntúan bien (Backend 55, DB 70, Testing/unit 55) pero la suma ponderada se derrumba por Mobile (12 — no compila), Seguridad (45 — sin mínimos prod), Funcionalidad de negocio (42 — flujos core rotos/fabricados) e Integraciones (40 — mercado ES falso). Evidencia dura: `page.tsx:148-156` inventa datos, `VehicleDrawer.tsx:402/349/452` manda `external_id` donde el backend exige UUID (500/404), el XML Android ni se parsea, y **no hay ni una pantalla de oportunidad/deal/simulación que cierre un flujo completo de punta a punta con datos reales**.

---

## 12) ¿QUÉ FALTA EXACTAMENTE PARA EL 100%?

1. **Que la app móvil compile**: merge conflict XML, `.env.local`, node_modules, versión Capacitor, FCM.
2. **Cerrar los 4 flujos core sin errores**: crear deal, simular beneficio, iniciar inspección, persistencia de búsqueda (hoy 500/404/vacíos).
3. **Eliminar todo mock activo por defecto**: fixtures ES desactivados y purgar `cached_market`.
4. **Sincronizar contratos UI↔API**: detalle/fases/feedback/status de oportunidad, repetir búsqueda.
5. **Seguridad mínima de producción**: CSRF o cookies HttpOnly, CSP, TRUSTED_HOSTS/HTTPS, rotar Firebase key, fix `npm audit`.
6. **CI honesta**: 22 integraciones en verde dentro del set de CI, `test_search_engine.py`, E2E real, vitest ≥70%.
7. **DevOps completo**: imagen prod sin dev-deps y no-root, métricas reales, CD, rollback, healthchecks.
8. **Desduplicar el repo**: clon, routers/schemas duplicados, `fix.bat`/`fix.js`.

---

## 13) ROADMAP HASTA EL 100% (orden por dependencias → criticidad → impacto → riesgo)

- **Fase 1 (semana 1) — Limpieza del árbol:** `AR-A-001` (integrar/eliminar clon) → `AR-A-002` (unificar routers) → `AR-A-003` (schemas) → `PV-P-001/002` (fixtures off + purge cache).
- **Fase 2 (semana 2) — Contratos de backend:** `BC-B-001` (deal) → `BC-B-002` (simular/inspección) → `BC-B-003` (persistencia) → `BC-B-006/011` (oportunidades, integración).
- **Fase 3 (semana 3) — Frontend real:** `FE-F-001/002/003` → `PR-U-001..004` → `MO-M-001..004` (móvil compila y arranca).
- **Fase 4 (semana 4) — CI y seguridad:** `DV-V-006`/`BC-B-011` (CI íntegra) → `SE-S-001/003/004` → `DB-D-001/002`.
- **Fase 5 (semanas 5-6) — Producción:** `DV-V-001..008` → `SE-S-002/005/006` → `MO-M-005/006` (FCM/push) → `BC-B-008/010`, `FE-F-006/007/008`.
- **Fase 6 (continuo) — Mejoras:** `FE-F-004/005/009/010`, `PR-U-005/006/007`, `DB-D-003/004`, `PV-P-003/004`, docs (`DO-D-001..004`), `AR-A-004/005`.

---

## 14) CONCLUSIÓN

Proyecto con **buena base técnica en backend y testing unitario** pero **invalidado como producto** por cinco razones probadas: (1) la app móvil no compila; (2) los flujos de oro están rotos (500/404 por el mal uso de `external_id`); (3) la UI fabrica datos que el backend no emite; (4) el "mercado español" se basa en fixtures sintéticos persistentes; y (5) hay un clon completo del repo con trabajo perdido que crea riesgo de divergencia.

**Nota global: 48/100 · No operable para su objetivo.**

Con las **18 tareas críticas** del BLOQUE A (≈4-6 semanas) la funcionalidad quedará utilizable; seguridad e integración móvil suben la nota a la zona 60-70 con el BLOQUE B; el 100% exige además desduplicación arquitectónica, CI honesta, CD y métricas reales.

**Prioridad inmediata:** un solo árbol de código, un solo contrato de IDs (UUID interno), y **cero datos inventados en pantalla**.