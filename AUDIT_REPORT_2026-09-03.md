# Auditoría Técnica Integral — ai-business-platform
Fecha: 2026-09-03 · Rama auditada: `audit-fixes` (HEAD `229f1fb`, divergida de `origin/main` con 34 commits no integrados)
Método: lectura directa de código (no documentación), ejecución real de `pytest`, `ruff`, `import app.main`, `alembic heads/history`, `docker compose config`, y 8 subagentes especializados por subsistema.

---

## A. Estado general

El proyecto es una plataforma de arbitraje de vehículos (comprar barato, revender con beneficio) con backend FastAPI + SQLAlchemy/Alembic/Postgres, frontend Next.js/Capacitor, scraping multi-provider, motor de scoring, motor económico (profit/ROI), motor de negociación, inspección por visión IA, y un CRM de deals.

**Hallazgo más importante: la aplicación no arranca.** `app/api/v1/opportunities.py:402` usa `BaseModel` sin importarlo de pydantic. Esto rompe `import app.main` con `NameError`, verificado directamente (`python -c "import app.main"`) y confirmado porque bloquea el 100% de la suite de tests (`pytest`: 15 errores de colección, 0 tests ejecutados). Es un bug trivial de una línea, pero su efecto es total: ni el backend arranca, ni el CI puede validar nada más allá de lint.

Descontando ese bloqueador (arreglo de una línea), el sistema tiene una arquitectura razonablemente madura y bastante más real de lo que un vistazo al TODO.md sugeriría: scoring, motor de negociación, orquestador de búsqueda multi-provider, y el CRM de deals con máquina de estados son código real, probado con arithmetic tests reales, no placeholders. Pero el **flujo de negocio completo no llega a cerrar el círculo**: la transición automática listing→opportunity→deal no existe (el único código que lo intenta está muerto y rompería si se llamara), no hay estados BOUGHT/IN_TRANSIT/REGISTERED/SOLD, y TRANSPORTE/MATRICULACIÓN/VENTA no existen como código — son solo líneas de coste estático.

Además hay dos bugs económicos silenciosos de alta prioridad que pueden distorsionar el ROI mostrado al usuario: el "precio competitivo" del scorer siempre da el máximo de puntos (no compara contra mercado), y el precio de venta por defecto es un multiplicador fijo ×1.4 sin base de mercado cuando no se pasa un precio real — ambos pueden generar señales de compra falsamente atractivas.

## B. Mapa funcional

| Módulo | Estado | Conectado | Tests | Real/Mock | Prioridad |
|---|---|---|---|---|---|
| Arranque de la app (`app.main`) | **ROTO** | — | Bloquea todo | — | **CRÍTICA** |
| Search / SearchOrchestrator | Implementado | Sí | Reales | Real | Alta |
| Providers AutoScout24 (DE/ES) | Implementado | Sí | Reales (fixtures HTML/JSON) | **REAL** (HTTP+parsing en vivo) | Alta |
| Provider mobile.de | Implementado | Sí (desactivado por defecto) | Reales | Real pero bloqueado por anti-bot (403 en prod) | Media |
| Provider coches.net (real) | Implementado | **NO registrado — código muerto** | Unit only | Real pero inalcanzable | Alta |
| Providers ES fixture (`es_market_fixture`, `coches_net_fixture`) | Implementado | Sí, por defecto | Reales | **FIXTURE** (sin HTTP) | Alta |
| Normalización | Implementado (implícito en parsers) | Sí | Parcial | Real | Media |
| Scoring (`VehicleScorer`) | Implementado | Sí | 63 tests | Real, pero "precio competitivo" es un no-op | Alta |
| Market (`ComparableMarketEstimator`) | Implementado | Sí | Sí | Real | Media |
| Costes (`import_costs.py`) | Implementado | Sí | Sí | Real, con constantes hardcoded | Media |
| Profit / ROI (`ProfitAnalyzer`) | Implementado | Sí | 92 tests (matemática real) | Real, con default de venta ×1.4 sin mercado | Alta |
| Opportunity Engine | Implementado | Sí (job periódico) | Sí | Real | Media |
| Negociación (`NegotiationEngine`) | Implementado (30KB) | Sí, dentro del flujo de búsqueda | Tests de integración reales | Real | Media |
| Inspección/Visión (OpenAI/Gemini) | Implementado | **Desconectado** del pipeline automático | Mocked | Real (API real) pero aislado | Alta |
| Deal / CRM | Implementado | Sí (manual) | Sí | Real, máquina de estados válida | Media |
| Negociación → Deal | No implementado | Output de negociación no se persiste en Deal | — | Falta | Media |
| Transporte / Matriculación / Venta | **No existe código** | — | — | Falta | Alta (gap funcional) |
| Orchestrator (`app/orchestrator/pipeline.py`) | Código muerto | No | No | Scaffolding sin usar | Baja |
| Agentes (`app/agents/*`) | Implementados | Sí (delegan a servicios reales) | Parcial | Real | Baja |
| Backend API (rutas) | Implementado | Mayormente sí | Bloqueados por AUD-001 | Real | Alta |
| Auth / Personal mode | Implementado, diseño sólido | Sí | Bloqueados por AUD-001 | Real | Media |
| Frontend | Implementado, sin placeholders | Parcial (3 páginas llaman APIs inexistentes) | Vitest — ver sección G | Real | Alta |
| Frontend↔Backend contrato | — | 3 mismatches duros, resto correcto | — | — | Alta |
| DB / Migraciones | Mayormente correcto | Falta 1 migración (`opportunity_phases`) | `alembic heads` limpio (1 head) | Real | Alta |
| Docker / Compose | Válido (`docker compose config` OK) | Sí | — | Real | Media |
| CI/CD | Implementado, con gaps | Sí | Lint frontend deshabilitado en CI | Real | Media |
| Seguridad | Buena base (CORS, rate limit, sin SQLi/cmd-injection) | — | — | — | Media |

## C. Problemas encontrados

### CRÍTICOS

**AUD-001**
Categoría: Backend / Runtime
Severidad: CRITICAL
Archivo: `app/api/v1/opportunities.py:402`
Problema: `class OpportunityFeedbackCreate(BaseModel)` sin `from pydantic import BaseModel, Field`.
Impacto: `import app.main` falla → la API **no arranca** → bloquea el 100% de `pytest` (15 errores de colección, 0 tests ejecutados) → bloquea validar cualquier otra cosa (auth, personal mode, CI de integración).
Solución: añadir `from pydantic import BaseModel, Field` al bloque de imports.
Code-only: YES

**AUD-002**
Categoría: Backend / Runtime
Severidad: CRITICAL
Archivo: `app/api/v1/deals.py:5,49`
Problema: se usa `HTTPException(...)` en la línea 49 pero solo se importa `APIRouter, Depends, Query, status` — falta `HTTPException`.
Impacto: `NameError` en tiempo real cuando la creación de un deal busca un vehículo por `source`+`external_id` y no lo encuentra (ruta alcanzable en producción).
Solución: añadir `HTTPException` al import de `fastapi`.
Code-only: YES

**AUD-003**
Categoría: Database / Migrations
Severidad: CRITICAL
Archivo: `app/models/opportunity_phase.py` vs `alembic/versions/*`
Problema: el modelo `OpportunityPhase` (tabla `opportunity_phases`) está activamente usado por endpoints reales (`GET/PATCH /opportunities/{id}/phases/...`), pero no existe ninguna migración que cree esa tabla.
Impacto: `alembic upgrade head` se ejecuta sin error, pero contra una BD limpia esos endpoints fallan con `relation "opportunity_phases" does not exist`.
Solución: generar migración Alembic para `opportunity_phases`.
Code-only: YES

**AUD-004**
Categoría: Database
Severidad: HIGH
Archivo: `app/models/opportunity_phase.py:29-38` vs `app/models/opportunity.py:26-27`
Problema: `OpportunityPhase.opportunity_id` es `String(36)` mientras que `Opportunity.id` (PK) es `Uuid(as_uuid=False)` nativo de Postgres — tipos de FK/PK incompatibles.
Impacto: en Postgres esto puede generar comparaciones/joins ineficientes o fallar el `ForeignKey` según el backend; ya existe precedente de que el equipo corrigió exactamente este patrón para `api_keys`/`refresh_tokens` (`f8a9b0c1d2e3_fk_user_id_api_keys_refresh_tokens.py`) pero no se aplicó aquí.
Solución: alinear tipo a `Uuid(as_uuid=False)` y añadir la migración junto con AUD-003.
Code-only: YES

### ALTOS

**AUD-005** — Providers / Scraping — HIGH
`app/providers/registry.py` importa `CochesNetProvider` solo bajo `TYPE_CHECKING` y `ensure_default_providers()` no lo registra nunca. El scraper real de coches.net (uno de los grandes portales españoles) es código muerto e inalcanzable en runtime; sólo se ejecuta en tests unitarios. Existe un fix ya hecho en `.worktrees/resolution/` (no mergeado) que sí lo registra.
Impacto: la búsqueda "ES" depende de datos de **fixture** (ver AUD-033) en vez del scraper real que sí existe y funciona.
Code-only: YES (registrar el provider, igual que ya se hizo en el worktree).

**AUD-006** — Providers — MEDIUM/HIGH
`app/providers/coches_net_html.py` y `app/providers/coches_net_html_fixture.py` definen **la misma clase** `CochesNetHtmlFixtureProvider`: la primera parsea HTML real de fixture, la segunda es un stub que siempre devuelve `[]`/`None`. El registry importa la correcta, pero el nombre duplicado es una trampa de mantenimiento — un import equivocado sustituiría datos reales por vacíos sin error visible.
Code-only: YES (renombrar/eliminar el stub).

**AUD-007** — Scoring — HIGH (impacto económico)
`app/services/vehicle_scorer.py:283-300` (`_evaluate_price`): cualquier vehículo con `price > 0` recibe automáticamente el 100% de los 20 puntos de "precio" (30% "precio definido" + 70% "precio competitivo"), sin comparar contra el mercado. Confirmado por `tests/unit/test_vehicle_scorer.py:234-238`, que codifica el bug como comportamiento esperado.
Impacto: la señal económica más importante del score (¿es un buen precio?) es un no-op. Un coche caro y uno barato con el mismo resto de campos reciben el mismo bonus de precio.
Solución: comparar contra `ComparableMarketEstimator` (que ya existe y se usa en otra parte del pipeline) para dar el bonus real.
Code-only: YES

**AUD-008** — Economía — HIGH (impacto económico)
`app/services/profit_analyzer.py:247,289-292`: si no se pasa `estimated_sale_price`, se usa `purchase_price * sale_price_multiplier` con `sale_price_multiplier` por defecto `1.4`. Este valor alimenta directamente `gross_profit`, `net_profit`, `roi_percentage`, `risk_level` y `recommendation`. Un markup del 40% garantiza casi siempre "beneficio" después de costes (~15-20%), por lo que cualquier ruta que no aporte un comparable de mercado real generará sistemáticamente recomendaciones BUY/CONSIDER infladas. Ningún test de `test_profit_analyzer.py` ejercita este camino por defecto (todos pasan `sale_price_multiplier` explícito).
Solución: exigir un precio de mercado real (fallar o marcar como `UNVERIFIED` en vez de asumir ×1.4) cuando no hay comparable.
Code-only: YES

**AUD-009** — Economía / Fiscalidad — HIGH (impacto económico)
No se diferencia vendedor particular (régimen de margen, ~10% efectivo) de empresa/concesionario (IVA pleno 21%). `app/services/iedmt.py:115-135` implementa correctamente `iedmt_plus_vat()` con `VAT_RATE_SPAIN=0.21` e IEDMT por tramos de CO2, pero **nunca se llama** desde `profit_analyzer.py` — solo se usa `iedmt_tax()` sumado al `tax_rate` plano del perfil (10% España). Confirmado: `iedmt_plus_vat` solo se referencia en su propio test.
Impacto: un vehículo comprado a un concesionario (IVA pleno) tiene su coste fiscal **subestimado en ~11% del precio de compra**, inflando artificialmente `net_profit`/`roi_percentage`.
Solución: añadir un campo "tipo de vendedor" y enrutar a `iedmt_plus_vat()` cuando corresponda.
Code-only: YES

**AUD-010** — Opportunity Engine — MEDIUM
`OpportunityRepository.list_filtered` (`app/repositories/opportunity_repository.py:172`) filtra por `Opportunity.status`, columna que **no existe** en el modelo → `AttributeError` si se invoca con `status` no nulo. El endpoint `GET /opportunities` acepta el parámetro `status` pero nunca lo reenvía a `list_filtered` (bug oculto detrás de otro bug: el parámetro no sirve para nada hoy, y si algún día se conecta, rompe).
Code-only: YES

**AUD-011** — Opportunity → Deal — HIGH (gap funcional + código roto)
`OpportunityIntegrationService.analyze_and_create_deal` (`app/services/opportunity_integration_service.py:17-36`) es el único código que intenta automatizar listing→opportunity→deal, y está muerto (cero llamadas fuera de su propio test) y roto si se llamara: llama `.get()` sobre un `OpportunityAnalysis` (dataclass, no dict) y pasa un `vehicle_id` como si fuera `opportunity_id` (violaría la FK).
Impacto: hoy la creación de deals es 100% manual vía `POST /deals`.
Code-only: YES (reescribir el servicio correctamente, o eliminarlo si no se va a usar).

**AUD-012** — Inspección — HIGH (desconexión silenciosa)
`SearchOrchestrator`/`SearchResultAnalyzer` nunca reciben un `inspection_service` real (`search_result_analyzer.py:52`, siempre `None`), así que `_load_inspection_result` siempre devuelve `None` y la negociación automática usa un `InspectionResult` heurístico vacío. Las fotos/observaciones reales de inspección (con IA de visión real, OpenAI/Gemini) nunca llegan a influir el scoring, el profit ni la negociación automática — solo quedan en la sesión de inspección aislada.
Code-only: YES (inyectar la dependencia).

**AUD-013** — Frontend — HIGH
Tres páginas del frontend (`useAgents.ts`, `useApprovals.ts`, `useWorkflows.ts`) llaman `GET /api/v1/agents`, `/approvals`, `/workflows` — **rutas que no existen en el backend**. Usan `fetch()` crudo (sin el cliente API compartido, sin refresh de auth). Estas páginas siempre fallarán con 404 en producción.
Code-only: YES (implementar backend o retirar las páginas).

**AUD-014** — Frontend↔Backend — HIGH
`useOpportunityDetail.ts` espera `{title, brand, model, year, status, price, market_price, margin, current_phase, agent_result, files[], activity_log[]}`; el backend real (`OpportunityReadDetail`, `opportunities.py:328-371`) devuelve `{id, vehicle, score, estimated_profit, roi_percentage, recommendation, risk_level, ..., phases[]}`. Ningún campo coincide. La página de detalle de oportunidad renderiza básicamente `undefined` en todas partes.
Code-only: YES

### MEDIOS

- **AUD-015** — `frontend/src/app/hooks/use-logout.ts` nunca llama `POST /auth/logout`; el refresh token no se revoca en servidor al cerrar sesión. Code-only: YES.
- **AUD-016** — `app/orchestrator/pipeline.py` (`PipelineOrchestrator`) es scaffolding muerto: no lo importa nada fuera de su propio archivo, ningún test lo ejercita, y su `run_pipeline` ni siquiera llama a los agentes que construye. Confunde sobre cuál es "el" orquestador real (`SearchOrchestrator`). Code-only: YES (eliminar o completar).
- **AUD-017** — Faltan índices en las FKs de las tablas de inspección (`vehicle_id`, `user_id`, `session_id`, `observation_id` en `inspection_sessions/observations/photos`), pese a que el equipo sí añade índices deliberadamente en otras migraciones (`p2q3r4s5t6u7`). Code-only: YES.
- **AUD-018** — `password_reset_token`, `verification_token`, `audit_log`: `user_id`/`resource_id` son `String(36)` sin `ForeignKey()` — integridad referencial no forzada por la BD. Code-only: YES.
- **AUD-019** — `.env.example` no documenta `OPENAI_API_KEY`/`GEMINI_API_KEY` (las claves de visión) — un despliegue nuevo cae en `MockVisionProvider` sin saber que existe la opción real. Code-only: YES (documentar en `.env.example`); **obtener las API keys reales es EXTERNAL ACTION REQUIRED**.
- **AUD-020** — `.env.example` le faltan ~15 variables que `Settings` sí lee (Redis password, JWT algorithm/previous secrets/expiración, flags de logging, tuning de search orders, etc.). Code-only: YES.
- **AUD-021** — `.env` real contiene variables que `Settings` ignora silenciosamente (`extra="ignore"`): `API_PREFIX`, `BCRYPT_ROUNDS`, `ENABLE_DOCS`, `LOG_FORMAT`, `PASSWORD_HASH_ALGORITHM` — no hacen nada, engañan al operador. Code-only: YES.
- **AUD-022** — `redis_url` declarado dos veces en `Settings` (la primera definición es código muerto); `redis_password` declarado pero nunca usado en ningún lado — configurarlo no protege nada. Code-only: YES.
- **AUD-023** — `/docs`, `/redoc`, `/openapi.json` no están condicionados por entorno — quedan expuestos también en producción. Code-only: YES.
- **AUD-024** — Subida de fotos de inspección (`routes/inspection.py:246-291`): sin límite de tamaño en servidor (buffer completo en memoria) y validación de content-type solo por lo que el cliente declara (sin chequeo de magic bytes). Code-only: YES.
- **AUD-025** — Docker: Postgres con credenciales hardcoded `postgres`/`postgres` y puerto publicado al host; Redis sin autenticación y puerto publicado; el mismo `docker-compose.yml` (con bind-mount de todo el repo) se usa para staging/producción vía `deploy.yml` — no hay separación dev/prod real. Code-only: parcialmente (separar compose files sí; asegurar el host real es EXTERNAL ACTION).
- **AUD-026** — `GRAFANA_ADMIN_PASSWORD` por defecto `admin` si no se define (perfil `obs`). Code-only: YES.
- **AUD-027** — `Dockerfile` sin `USER` (corre como root), instala dependencias de dev/test (`uv sync --group dev`) en la imagen de runtime. Code-only: YES.
- **AUD-028** — Lint de frontend deshabilitado en CI (`ci.yml:136-138`, comentado "pending CI.LINT.1"). Code-only: YES.
- **AUD-029** — 31 errores de `ruff` en `app/` (21 auto-corregibles): imports sin usar, redefiniciones, incluido el import muerto relacionado con AUD-006. Code-only: YES (`ruff check --fix`).
- **AUD-030** — Regex genérico de precio/kilometraje en `base.py:545-595` escanea **todo el texto de la página** como último recurso (no solo el nodo del listing) — riesgo de capturar un número de un widget no relacionado sin lanzar error. Code-only: YES (acotar el scope del regex al nodo).
- **AUD-031** — `mobile_de` no fija `currency` en el parser base (solo AutoScout24 lo hace explícitamente) — si algún día se reactiva, sus precios no llevan etiqueta de moneda. Code-only: YES.

### INFO / bajo riesgo
- `DealStatus` no tiene `NEGOTIATING` explícito (solo `OFFER` cubre esa fase) — cuestión de nomenclatura, no bug.
- Redis no tiene servicio en CI (aceptable, hay fallback in-memory documentado).
- `AccessLogMiddleware` loguea el query-string completo; hoy ningún endpoint sensible usa query params, pero es un riesgo latente si cambia.

## D. Funcionalidades faltantes

1. **Transición automática listing → opportunity → deal.** Hoy es 100% manual.
2. **Estados de Deal para el ciclo completo**: `BOUGHT`, `IN_TRANSIT`, `REGISTERED`, `SOLD` no existen — `DealStatus` termina en `WON`/`LOST`/`DROPPED`. No hay concepto de "beneficio realmente obtenido" tras la venta.
3. **Etapa TRANSPORTE**: ni modelo, ni servicio, ni agente. Solo coste estimado estático.
4. **Etapa MATRICULACIÓN**: igual — no hay integración con DGT ni ningún flujo, solo coste.
5. **Etapa VENTA**: no existe ningún modelo/servicio de reventa/publicación del vehículo tras la compra.
6. **`LogisticsAgent`**: referenciado implícitamente por una fase sembrada ("Importación… transporte, matriculación e impuestos", `agent="logistics"`) pero la clase no existe en absoluto.
7. **Persistencia del resultado de negociación en el Deal**: `NegotiationEngine` calcula oferta/contraoferta/leverage, pero ese resultado no se guarda en el registro de `Deal` — se pierde tras la sesión de búsqueda.
8. **Historial/auditoría de cambios de estado del Deal**: no hay tabla de histórico, solo el campo `status` actual se sobrescribe.
9. **Diferenciación particular/empresa en el motor fiscal** (ver AUD-009) — el código para IVA pleno existe pero no está conectado.
10. **Panel de administración de usuarios en frontend**: el backend tiene CRUD completo de `/users` y roles; no hay UI.
11. **Verificación de email / reset de password en frontend**: rutas de backend completas, sin UI.

## E. Código implementado pero desconectado

- `app/providers/coches_net.py` (scraper real de coches.net) — nunca registrado (AUD-005).
- `app/services/inspection_service.py` + providers de visión IA reales — aislados del pipeline automático (AUD-012).
- `app/services/opportunity_integration_service.py` y `app/services/deal_pipeline_integration_service.py` — solo llamados por sus propios tests.
- `app/orchestrator/pipeline.py` (`PipelineOrchestrator`) — scaffolding sin ningún caller externo.
- `app/services/iedmt.py::iedmt_plus_vat()` — implementado y testeado, pero jamás invocado desde el flujo real de profit.
- Backend `/users`, `/vehicles/{id}` PATCH/DELETE, `/vehicles/{id}/evaluation`, `/opportunities/cursor`, `/opportunities/export/csv`, `/budget-search/search`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/verify`, `/notifications/send` — con backend funcional, sin ninguna UI que los consuma.

## F. Código sospechoso

- Dos clases con el mismo nombre `CochesNetHtmlFixtureProvider` en archivos distintos, una real y una stub (AUD-006).
- `redis_url` duplicado en `Settings` (AUD-022).
- Variables de `.env` que `Settings` ignora silenciosamente (AUD-021).
- `iedmt_plus_vat()` correctamente implementado y probado, pero completamente huérfano — trabajo ya hecho que nadie conectó.
- `frontend`: tres hooks (`useAgents`, `useApprovals`, `useWorkflows`) construidos sobre endpoints que nunca existieron en el backend — páginas fantasma.
- `.worktrees/resolution/` contiene una versión del `registry.py` que sí arregla AUD-005/registro de coches_net, sugiriendo trabajo en curso no fusionado a esta rama.
- `mobile_router` montado dos veces en `app/main.py` (dentro de `api_router` y otra vez de forma directa) — duplicación inofensiva pero descuidada.

## G. Tests

**Backend (`pytest`, vía `.venv/Scripts/python.exe -m pytest -q`):**
- Total: **0 ejecutados**
- Passing: 0
- Failing: 0
- Errors de colección: **15** (todos por el mismo `NameError: name 'BaseModel' is not defined` propagado desde `app/api/v1/opportunities.py:402`, que rompe `app.main` y por tanto cualquier test que importe la app)
- Módulos bloqueados: `tests/e2e/test_backend_flows.py`, `tests/integration/*`, `tests/security/test_cors.py`, y 10 archivos más de `tests/unit/`
- Cobertura: no disponible (no llegó a ejecutarse ningún test)
- Conclusión: **el CI backend actualmente no puede validar absolutamente nada** más allá de lint y migraciones — la propia pipeline de CI en `.github/workflows/ci.yml` correría contra este mismo bug si se ejecutara hoy sobre este working tree.

**Lint backend (`ruff check app/`):** 31 errores, 21 auto-corregibles (imports sin usar, redefiniciones) — ver AUD-029.

**Frontend (`npx vitest run` desde `frontend/`):** **34 archivos de test, 210 tests — todos PASS.** El lint de ESLint, sin embargo, está deshabilitado en CI (AUD-028), así que "tests en verde" no implica que el lint pase; y ninguno de estos 210 tests habría detectado los mismatches de contrato de AUD-013/AUD-014 porque son tests unitarios de componentes/hooks, no tests de contrato contra el backend real.

**Tests que sí son sustantivos (no solo mocks) cuando SÍ corren:**
- `test_profit_analyzer.py` (92 tests): aritmética real verificada (gross/net/margin calculados y comparados).
- `test_vehicle_scorer.py` (63 tests): edge cases reales (precio negativo, kilometraje 0, campos vacíos) — aunque no detecta el bug de AUD-007 porque lo codifica como esperado.
- `test_negotiation_integration.py` (668 líneas): lógica de negocio real a través del pipeline.
- Tests de providers: mockean `httpx`/HTML fixtures — contract tests válidos, pero **ninguno golpea la web real** (esperado y correcto para CI).

## H. Auditoría E2E — ¿hasta dónde llega el flujo hoy?

```
SEARCH ✅ → SCRAPING ⚠️(parcial: AS24 real, ES fixture/coches.net muerto) → NORMALIZACIÓN ✅
→ SCORING ⚠️(precio competitivo es no-op) → MARKET ✅ → COSTES ⚠️(fiscalidad particular/empresa incompleta)
→ PROFIT ⚠️(default de venta sin mercado real) → OPPORTUNITY ✅ → NEGOCIACIÓN ✅ (pero no se persiste en Deal)
→ INSPECCIÓN ✅ (aislada, no conectada automáticamente) → DEAL ✅ (manual, máquina de estados válida)
→ TRANSPORTE ❌ (no existe) → MATRICULACIÓN ❌ (no existe) → VENTA ❌ (no existe)
```

**Primer punto de ruptura real (bloqueante, no solo incompleto): el arranque de la aplicación (AUD-001).** Hasta que no se corrija, nada de lo anterior es verificable en ejecución real, aunque el código subyacente exista.

**Primer punto de ruptura estructural (asumiendo AUD-001 corregido):** la transición automática **Opportunity → Deal** no existe (AUD-011) — un usuario puede llegar hasta tener oportunidades scoreadas automáticamente, pero crear el Deal es un paso manual. A partir de ahí, todo lo que viene después de "WON" (transporte, matriculación, venta) simplemente no tiene código.

## I. Roadmap de implementación (bloques grandes)

**TASK 1 — Desbloqueo crítico (arranque + BD)**
Arreglar AUD-001, AUD-002 (imports faltantes), AUD-003/AUD-004 (migración `opportunity_phases` + tipo de FK). Sin esto nada más es verificable. Esfuerzo: horas, no días.

**TASK 2 — Integridad económica (Scoring + Profit + Fiscalidad)**
AUD-007 (precio competitivo real usando `ComparableMarketEstimator`), AUD-008 (eliminar/condicionar el multiplicador ×1.4 sin mercado), AUD-009 (conectar `iedmt_plus_vat` para vendedor empresa/IVA pleno). Este bloque corrige que el ROI mostrado hoy pueda estar sistemáticamente inflado.

**TASK 3 — Cierre del pipeline Opportunity → Deal → Transporte/Matriculación/Venta**
AUD-011 (reescribir la transición automática), AUD-010 (filtro de status), diseñar y construir las etapas TRANSPORTE/MATRICULACIÓN/VENTA (nuevos modelos+servicios+endpoints), añadir estados `BOUGHT/IN_TRANSIT/REGISTERED/SOLD` a `DealStatus`, persistir el resultado de negociación en el Deal.

**TASK 4 — Providers España reales**
AUD-005 (registrar `coches_net` real), AUD-006 (eliminar clase stub duplicada), decidir estrategia para mobile.de (proxies residenciales — EXTERNAL ACTION) o aceptarlo como desactivado permanentemente.

**TASK 5 — Conectar Inspección/Visión al pipeline automático**
AUD-012 (inyectar `inspection_service` real en `SearchOrchestrator`/`SearchResultAnalyzer`), documentar y exigir `OPENAI_API_KEY`/`GEMINI_API_KEY` en `.env.example` (AUD-019 — obtención de las keys es EXTERNAL ACTION).

**TASK 6 — Contrato Frontend↔Backend**
AUD-013 (implementar o retirar `/agents`, `/approvals`, `/workflows`), AUD-014 (arreglar shape de `useOpportunityDetail`), AUD-015 (logout revoca token en servidor). Construir UI para capacidades backend huérfanas (users admin, password reset, budget-search) donde tenga sentido de producto.

**TASK 7 — Limpieza de código muerto/duplicado**
AUD-016 (`PipelineOrchestrator`), AUD-006, AUD-029 (`ruff --fix`), consolidar `redis_url`/`redis_password` (AUD-022), limpiar `.env`/`.env.example` (AUD-020, AUD-021).

**TASK 8 — Endurecimiento de seguridad y Docker/CI**
AUD-023 (gatear `/docs` por entorno), AUD-024 (límite de tamaño/validación de subida de imágenes), AUD-025/AUD-026/AUD-027 (separar compose dev/prod, credenciales por defecto, usuario no-root en Dockerfile), AUD-028 (reactivar lint frontend en CI).

**TASK 9 — Índices e integridad referencial de BD**
AUD-017 (índices en tablas de inspección), AUD-018 (FKs faltantes en tokens/audit_log).

## J. Prioridad de ejecución

1. **TASK 1** — bloqueante absoluto, nada más se puede validar sin esto.
2. **TASK 2** — produce datos económicos incorrectos (ROI inflado) que podrían llevar a decisiones de compra equivocadas con dinero real.
3. **TASK 3 + TASK 4** — necesarios para que el flujo E2E completo (SEARCH→VENTA) sea real y no se apoye en datos de fixture.
4. **TASK 5 + TASK 6** — calidad funcional: conectar trabajo ya hecho (inspección) y arreglar contrato frontend/backend.
5. **TASK 7** — calidad de código.
6. **TASK 8 + TASK 9** — endurecimiento y performance, importantes antes de cualquier despliegue expuesto a internet pero no bloqueantes para uso personal local.

---

## Verificación de estado del repositorio

`git status` al finalizar la auditoría: **sin cambios funcionales introducidos por esta sesión** (solo se ejecutaron lecturas, `pytest`, `ruff check` sin `--fix`, `python -c "import app.main"`, `alembic heads/history`, `docker compose config` — ninguno escribe en el repo). El único archivo modificado (`frontend/package-lock.json`) y los archivos sin trackear (`.openclaw.json`, `.worktrees/`, `TASK_AUTONOMO.md`) ya estaban presentes antes de iniciar esta auditoría.

**Siguiente task recomendado: TASK 1 (Desbloqueo crítico).** Es un cambio de minutos (dos imports faltantes + una migración) que desbloquea la validación real de todo lo demás.
