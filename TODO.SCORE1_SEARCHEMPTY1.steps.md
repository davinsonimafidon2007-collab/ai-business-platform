# SCORE.1 + SEARCH.EMPTY.1 — DONE

Fecha: 2026-08-06

## Hecho

- [x] SCORE.1: `category_key` + `category_label_es` en `vehicle_scorer`, schema, mapper search, types, drawer
- [x] `category` legacy sigue en español (compat tests)
- [x] SEARCH.EMPTY.1: error/empty ES + hint Admin/providers en `frontend/src/app/search/page.tsx`
- [x] `pytest tests/unit/test_vehicle_scorer.py` → 78 passed
- [x] `cd frontend; npx tsc --noEmit` → 0 errores

## Archivos tocados

- app/services/vehicle_scorer.py
- app/api/v1/schemas/common.py
- app/api/v1/routes/search.py
- frontend/src/app/types/vehicle.ts
- frontend/src/app/features/vehicle/VehicleDrawer.tsx
- frontend/src/app/search/page.tsx
- tests/unit/test_vehicle_scorer.py

## Pendiente solo operador

- [ ] `git add` / `commit` / `push` desde la **raíz** del repo (no solo `frontend/`)

## No reabrir

No regenerar category maps ni empty states salvo bug reportado.
