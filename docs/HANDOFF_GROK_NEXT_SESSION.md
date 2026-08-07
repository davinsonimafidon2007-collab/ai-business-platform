# HANDOFF — AI Business Platform (importación coches DE → ES)

Documento para la **siguiente sesión / otra cuenta**. No rehacer lo marcado como hecho.

Última actualización: 2026-08-06 (SCORE.1 + SEARCH.EMPTY.1 cerrados en local; commit desde raíz pendiente si el working tree aún tiene cambios).

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

## 3. Estado general (~75–80% local)

| Ámbito | Notas |
|--------|--------|
| Backend core | Search pipeline, profit, score, negotiation, opportunities |
| Providers DE | AS24 live OK (parser `__NEXT_DATA__`); mobile.de 403 sin proxy |
| Labels ES | ROI coherence, REC labels, OPP labels, SCORE category_key, cost_lines |
| Frontend | Search empty/error ES, drawer labels, admin |
| Ops / prod | Proxy, SMTP real, Firebase SA, deploy — pendientes de credencial |

---

## 4. Tasks completadas (NO rehacer)

| Task | Resumen |
|------|---------|
| Providers 1b | `VehicleProvider`; AS24 `__NEXT_DATA__`; mobile.de anti-bot 403 |
| MKT.1 / MKT.2 | `explanation` en market estimation + UI |
| PROFIT.1 | `cost_lines` + `cost_breakdown_labels.py` |
| ROI.1 | `app/services/profit_coherence.py` → `coherence_warnings` en mapper search |
| REC.1 | `app/services/recommendation_labels.py` (risk + recommendation ES) |
| OPP.LIST.1 | `OpportunityRead` + `opportunities.py` con `*_label_es` |
| SCORE.1 | `category_key` + `category_label_es` (category legacy sigue en ES) |
| SEARCH.EMPTY.1 | Empty/error search en ES + hint Admin/providers |
| NEG.1 | Drawer: Apertura / defectos / mercado / Cierre |
| E2E.1 / SMOKE | `scripts/smoke_critical_path.py` + README |
| H.1–H.2, E.3–E.4, G.3–G.4, N.1, J.1, T.1, INT.1, etc. | Ver historial git / releases anteriores |

### Dónde vive cada cosa

- Coherence: `app/services/profit_coherence.py` (se aplica en `app/api/v1/routes/search.py`, no cambia fórmulas).
- Labels rec/risk: `app/services/recommendation_labels.py`.
- Score keys: `app/services/vehicle_scorer.py` (`SCORE_CATEGORY_LABELS_ES`, `category_key`).
- Schema API: `app/api/v1/schemas/common.py`, `opportunity.py`.

---

## 5. Bloqueos por credencial (no son bugs de código)

| ID | Qué falta |
|----|-----------|
| A.5b | `PROVIDER_HTTP_PROXY` o cookies reales para mobile.de (403) |
| SMTP | Credenciales SMTP reales (código de alertas listo) |
| FIRE | Service account / config Firebase |
| AS24-ES live | Flag + red; fixture offline ≠ live |

---

## 6. No hacer

- Regenerar todas las migraciones Alembic “por estética”.
- Reimplementar `profit_coherence` o `recommendation_labels` desde cero.
- Cambiar fórmulas de ROI / umbrales SCORE sin task explícito.
- Editar `requirements.txt` a mano (usar uv export).
- Commit solo desde `frontend/` (se dejan fuera `app/`, tests, docs).

---

## 7. Comandos útiles

```powershell
$env:ENVIRONMENT="test"
$env:JWT_SECRET_KEY="test_secret_key_that_is_at_least_32_characters_long_1234567890"

pytest tests/unit/test_vehicle_scorer.py tests/unit/test_profit_coherence.py tests/unit/test_recommendation_labels.py -q
cd frontend; npx tsc --noEmit; cd ..
python scripts/smoke_critical_path.py
python scripts/release_check.py --skip-smoke
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

## 9. Prioridad siguiente

1. **Operador:** asegurar commit/push en `main` de SCORE.1 + SEARCH.EMPTY.1 (+ este HANDOFF/TODO) desde la raíz.
2. **Producto ligero:** e2e manual search → drawer (ver labels ES y coherence_warnings).
3. **Ops con credencial:** A.5b proxy mobile.de → SMTP → Firebase.
4. **Largo plazo:** portales ES live (P.1b+); no tratar fixtures como scrapers live.

---

## 10. Reglas

- No secretos en git.
- Preferir fixtures antes de tocar parsers en vivo.
- Alertas no deben tumbar el scheduler.
- `release_check --skip-smoke` debe seguir verde en CI local razonable.

---

*Fin HANDOFF. Actualizar este archivo al cerrar cada par de tasks de producto.*
