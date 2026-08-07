# HANDOFF — AI Business Platform (importación coches DE → ES)

Documento para la **siguiente sesión / otra cuenta**. No rehacer lo marcado como hecho.

Última actualización: 2026-08-07

**Contexto (2026-08-07):** uso **personal y local**, no despliegue SaaS.  
Documento ampliado: [docs/CONTEXT_PERSONAL_USE.md](CONTEXT_PERSONAL_USE.md).

- Infra: PC local suficiente; VPS opcional solo para 24/7.
- Datos DE: priorizar **AutoScout24**; mobile.de no prioritario (403 / ToS / sin proxy residencial de pago).
- SMTP y Firebase: **opcionales**.
- No gastar en proxy residencial como base del MVP personal.

Incluye:
labels ES (PROFIT/REC/ROI/SCORE/NEG/OPP), MKT explanation/sources, providers ES
fixtures + registry, ADMIN providers UI, SIM.1, E2E.MANUAL.1, SMOKE.CRIT.1.

---

## 1. Qué es el proyecto

Backend FastAPI + frontend Next.js para:

1. Buscar vehículos en portales DE (mobile.de, AutoScout24).
2. Puntuar, estimar mercado, calcular costes de importación y ROI.
3. Recomendar comprar / considerar / descartar y script de negociación.
4. Listar oportunidades, deals, admin/status, API keys.

Visión futura (NO implementada como portales live ES): comparables coches.net / milanuncios / wallapop / AS24-ES. Hoy hay fixtures ES opcionales (`es_market_fixture`, etc.), no scrapers live de España.

---

## 2. Stack

| Capa | Tech |
|------|------|
| Backend | FastAPI, SQLAlchemy async, Alembic, Python 3.13 |
| Auth | JWT, API keys, USER/ADMIN, Firebase opcional |
| Jobs | Scheduler, canary providers, refresh opportunities |
| Frontend | Next.js, React Query, TypeScript |
| Tests | pytest unit/integration; Vitest frontend |
| Deps | `pyproject.toml` + `uv.lock` → no editar `requirements.txt` a mano |

---

## 3. Estado general (~80% local usable)

| Ámbito | Estado |
|--------|--------|
| Backend core | Search, profit, score, negotiation, opportunities, simulate-profit |
| Labels / UX ES | cost_lines, recommendation/risk, score category, coherence_warnings, empty search |
| Market | explanation + provider_sources + cache column |
| Providers DE | AS24 OK; mobile.de 403 sin proxy |
| Providers ES | fixtures offline + AS24-ES flag; no scrapers live ES |
| Admin / ops scripts | providers snapshot, health compuesto, smoke crítico, integrations ready |
| Infra local | Postgres + **Redis** en docker-compose |
| CI | unit + Postgres service + alembic + INT.1 subset |
| Prod / credencial | proxy, SMTP real, Firebase SA — pendientes |

% orientativo: **~80% local usable**; **ops live** sigue bajo sin credenciales.

---

## 4. Tasks completadas (NO rehacer)

| Task | Nota breve |
|------|------------|
| CI.1 / CI.2 | Actions + Postgres + INT.1 |
| MKT.1–3 / MKT.1b | explanation, API, provider_sources, columna cache |
| P.1a–d / DEST.1 | fixtures ES, registry boot, AS24-ES, HTML coches |
| ADMIN.1 / 1b | API + UI providers |
| SMOKE.ES / OPS.READY / SMOKE.CRIT.1 | scripts + admin providers en smoke |
| E2E.MANUAL.1 | `docs/E2E_MANUAL_CHECKLIST.md` |
| PROFIT.1 / REC.1 / ROI.1 / SCORE.1 / NEG.1 / OPP.LIST.1 | labels y warnings |
| SIM.1 | simulate-profit alineado search |
| HYGIENE / TEST.WIN.1 / CODE-001 | basura raíz, sqlite skip, dead code |
| INFRA Redis Compose | servicio redis en compose |
| DEVOPS-001 | health compuesto, backup scripts, docs/ops.md |
| HEALTH.UI.1 | health compuesto en admin UI (chips api/db/redis) |
| SEC.001 | CORS prod + firebase_required |
| ARCH-002 / PERF-001 / ECON-001 / FE-001 | según TODO ✅ del repo |

### Dónde vive cada cosa

- Coherence: `app/services/profit_coherence.py` (se aplica en `app/api/v1/routes/search.py`, no cambia fórmulas).
- Labels rec/risk: `app/services/recommendation_labels.py`.
- Score keys: `app/services/vehicle_scorer.py` (`SCORE_CATEGORY_LABELS_ES`, `category_key`).
- Schema API: `app/api/v1/schemas/common.py`, `opportunity.py`.
- simulate-profit: `app/api/v1/vehicles.py` (`simulate-profit`), `frontend/src/app/services/simulateProfit.ts`.

---

## 5. Bloqueados por credencial (código listo)

| ID | Falta |
|----|-------|
| A.5b | `PROVIDER_HTTP_PROXY` / sesión mobile.de |
| SMTP.1 live | cuenta SMTP |
| FIRE.1 live | service account |
| AS24-ES live | flag + red estable |

---

## 6. No hacer

- No regenerar todas las migraciones Alembic “por estética”.
- No reimplementar `profit_coherence` / `recommendation_labels` / `cost_breakdown_labels`.
- No editar `requirements.txt` a mano (uv).
- No tratar fixtures ES como scrapers live.
- No meter `smoke_critical_path` en CI sin admin secrets + API estable.
- Commit solo desde `frontend/` (se dejan fuera `app/`, tests, docs).
- No asumir que un VPS datacenter (~5 €) desbloquea mobile.de.
- No priorizar compra de proxy residencial para uso personal del MVP.
- No tratar A.5b-LIVE como gate de release personal.

---

## 7. Comandos útiles

```powershell
python scripts/check_integrations_ready.py
python scripts/smoke_es_providers.py
python scripts/release_check.py --skip-smoke

# API up:
python scripts/smoke_critical_path.py
python scripts/smoke_critical_path.py --with-opportunities
python scripts/smoke_critical_path.py --with-admin
```

Commit desde **raíz del repo**:

```powershell
cd "C:\Users\davin\Documents\agentes de ia"
git add -A
git status
git commit -m "mensaje claro"
git push origin main
```

---

## 8. Formato de tasks (para el agente)

Cada task: título, precondiciones, objetivo, no tocar, FIX 1..N **con código/texto paste-ready**, verificación, aceptación, fuera de alcance, siguiente.

Preferir **aplicar texto dado** antes que generar código nuevo.

---

## 9. Prioridad siguiente (uso personal — 2026-08-07)

1. Usar el flujo local AS24 → drawer → simulate → opportunities.
2. Ejecutar una vez `docs/E2E_MANUAL_CHECKLIST.md` y anotar fecha PASS.
3. (Opcional) SMTP.LIVE — mails a la bandeja personal.
4. (Opcional) FIRE.LIVE — login Google.
5. **A.5b mobile.de / proxy residencial: NO prioritario** (aparcado).
6. Largo plazo: fuente autorizada o fixtures; no “bypass anti-bot” como roadmap.

### Bloqueos por credencial (siguen existiendo, no bloquean el MVP personal)

| ID | Notas |
|----|--------|
| A.5b | Proxy/cookies — **no planificado** en uso personal |
| SMTP | Solo si se quieren alertas email |
| FIRE | Solo si se quiere Google login |

Sin estos, jwt + database + AS24 + fixtures ES bastan.

---

## 10. Reglas

- No secretos en git.
- Preferir fixtures antes de tocar parsers en vivo.
- Alertas no deben tumbar el scheduler.
- `release_check --skip-smoke` debe seguir verde en CI local razonable.

---

*Fin HANDOFF. Actualizar este archivo al cerrar cada par de tasks de producto.*
