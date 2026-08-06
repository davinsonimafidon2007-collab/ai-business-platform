# HANDOFF — ai-business-platform (siguiente sesión Grok)

**Fecha:** 2026-08-06  
**Propósito:** leer este archivo **antes** de proponer código o tasks. Continuidad entre chats de IA.

---

## 1. Qué es el proyecto

Plataforma de **importación de vehículos Alemania → España/Portugal**:

1. Buscar en **mobile.de** y **AutoScout24** (DE/EU).
2. Analizar precio, km, año, estado, etc.
3. Estimar **costes de importación** (perfil SPAIN/PORTUGAL: transporte, matriculación, ITV, impuestos, gestoría, reparaciones).
4. Estimar margen / riesgo / recomendación (BUY / CONSIDER / REJECT; negociación WALK_AWAY / NEGOTIATE / BUY).
5. Pipeline de **deals** (NEW → CONTACTED → OFFER → …) + simulación de margen + prefill de oferta.

### Visión de producto — comparador mercado ES (NO IMPLEMENTADA)

Norte del usuario (aún no hay código de portales ES):

1. Buscar en Alemania (mobile.de, AutoScout24 DE, otros).
2. Analizar el vehículo.
3. Estimar coste de importación.
4. **Comparar con mercado español:** coches.net, AutoScout24 España, milanuncios, wallapop motor (si viable), datos históricos propios.
5. Calcular precio medio ES, venta esperada, beneficio bruto/neto, riesgo.
6. Recomendación: comprar / negociar / no comprar.
7. Ideal: la IA **explica el diferencial** (oferta, demanda, acabado, color, días en mercado, % bajo mercado).

**Hoy NO existen** providers `coches.net`, `milanuncios`, AS24-ES ni wallapop.  
El “lado España” actual es solo:

- perfiles de coste `SPAIN` / `PORTUGAL` en `app/config/import_costs.py`
- `estimated_sale_price` en simulación (manual o estimado)
- `ComparableMarketEstimator` con comparables de providers registrados (**solo** `mobile_de` + `autoscout24`) — con `explanation` legible del diferencial ya hecha (MKT.1); search API + drawer ya muestran `explanation` (MKT.2); portales ES siguen sin implementar


Añadir portales ES = trabajo nuevo (provider + estimador + fixtures). No tratarlo como hecho.

> **P.1a (2026-08-06):** ya existe un provider **offline** de comparables ES
> (`EsMarketFixtureProvider`, `source_name="es_market_fixture"`) que carga
> fixtures JSON (`app/providers/fixtures/es_market_sample.json`) y se registra en
> `ProviderRegistry` con el flag `ENABLE_ES_MARKET_FIXTURE` (default off). Sin
> red. Los portales live ES (coches.net / milanuncios / wallapop / AS24-ES)
> siguen **pendientes** → P.1b+.
>
> **P.1a-bis (2026-08-06):** `ProviderRegistry.ensure_default_providers()` registra
> `mobile_de` y `autoscout24` siempre, y `es_market_fixture` solo si
> `ENABLE_ES_MARKET_FIXTURE=true`. Se invoca en `get_market_estimator` y en
> `scheduler_lifespan` (boot), así que `_search_comparables` siempre ve al menos
> los providers DE en runtime.

---

## 2. Stack

| Capa | Tech |
|------|------|
| Backend | FastAPI, SQLAlchemy async, Alembic, Python **3.13** (evitar 3.14 en Windows: lxml) |
| Auth | JWT, API keys, USER/ADMIN, Firebase opcional |
| Jobs | Scheduler, canary providers, refresh opportunities |
| Cache / RL | Redis opcional |
| Frontend | Next.js app router, React Query, TypeScript |
| Tests | pytest unit + integration crítico; Vitest frontend |
| Deps | `pyproject.toml` + `uv.lock` → `requirements.txt` GENERATED (no editar a mano) |

---

## 3. Estado general (~70–75% local)

| Ámbito | % | Notas |
|--------|---|--------|
| Backend core | 75–85% | deals, N.1 negociación, J.1 alertas |
| Providers DE | 55–65% | AS24 live OK; mobile.de 403 sin proxy |
| Frontend | 70–80% | deals, opportunities, API keys, admin |
| Calidad | ~80%+ | ~897 unit; ~47 integration crítico |
| Ops / prod | 25–40% | proxy, SMTP real, Firebase, deploy |

Local: app abre y funciona con DB migrada + `.env`.  
Smoke: `scripts/smoke_critical_path.py` (register → vehicle → deal → simulation → OFFER).

---

## 4. Tasks completadas (NO rehacer)

| Task | Resumen |
|------|---------|
| H.1 | Frontend API keys propias `/api-keys` |
| H.2 | Admin API keys list/revoke |
| E.3 | Prefill offer_price desde last_sim_purchase_price |
| E.4 | Deal.id al crear; crear+guardar simulación |
| G.3 | Admin status + canary UI |
| G.4 | Admin status: métricas jobs |
| N.1 | net_profit ≤ 0 → WALK_AWAY |
| S.1 | Tests consecutive_failures |
| M.1 | Fixture mobile.de 3+1 |
| R.1 | requirements vía uv export |
| C.1 | check_requirements_sync.py |
| J.1 | Alertas email racha jobs |
| E2E.1 / E2E.2 | smoke_critical_path + flags |
| REL.1 | release_check.py |
| T.1 | Unit suite verde |
| INT.1 | Integration crítico; `--with-integration` |
| A.5b | BLOQUEADA POR CREDENCIAL (403 mobile.de) |

---

## 5. Bloqueos por credencial

- **A.5b:** `PROVIDER_HTTP_PROXY` o cookies. Código listo. AS24 live OK.
- **SMTP.1:** J.1/C.2 listos; falta SMTP real.
- **FIRE.1:** Google/Firebase pendiente de credenciales.

No son bugs de código.

---

## 6. Comandos

```powershell
$env:ENVIRONMENT="test"
$env:JWT_SECRET_KEY="test_secret_key_that_is_at_least_32_characters_long_1234567890"

python scripts/release_check.py --skip-smoke
python scripts/release_check.py --skip-smoke --with-integration
python scripts/smoke_critical_path.py
python scripts/check_requirements_sync.py
uv run python scripts/verify_providers_live.py
```

---

## 7. Rutas clave

- `app/services/negotiation_engine.py`
- `app/config/import_costs.py`
- `app/providers/mobile_de.py`, `autoscout24.py`
- `app/services/comparable_market_estimator.py`
- `frontend/src/app/deals/`, `offerPrefill.ts`, `features/simulate/`
- `app/api/v1/admin_status.py`, `frontend/src/app/admin/page.tsx`
- `app/jobs/scheduler.py`, `app/services/job_failure_alert_service.py`
- `scripts/release_check.py`, `smoke_critical_path.py`, `check_requirements_sync.py`

---

## 8. Formato de tasks

Si el usuario pide “siguiente task”: título, precondiciones, objetivo, no tocar, FIX 1..N, verificación, aceptación, fuera de alcance, siguiente.

---

## 9. Prioridad siguiente

1. SMTP.1 (o documentar bloqueo)
2. FIRE.1 (si hay credenciales)
3. A.5b al tener proxy
4. Largo plazo: **P.1 provider mercado ES** + explicación diferencial (visión; no implementado)

---

## 10. Reglas

- No editar `requirements.txt` a mano
- No secretos en git
- Preferir fixtures antes de cambiar parsers
- Alertas no tumban el scheduler
- `release_check --skip-smoke` debe seguir verde

---

*Actualizar este archivo o TODO.md al cerrar tasks nuevas.*
