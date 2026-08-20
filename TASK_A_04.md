# TASK_A_04 — Anadir CI basica y cohesionar e2e

## Problema
`.github/workflows/` no existe, por lo que no hay validacion automatica
de backend/frontend ni seguridad. Ademas, `package.json` no define
script e2e unificado.

## Archivos a modificar
- `.github/workflows/ci.yml` (nuevo)
- `frontend/package.json`

## Accion
- Anadir workflow con instalacion, pytest, ruff y build frontend.
- Para frontend, definir `test:e2e` en `package.json` y el paso en CI
  segun herramienta elegida (Playwright o Maestro).

## Criterio de aceptacion
- CI corre en push/PR y reporta estado.
- `npm run test:e2e` existe y es invocable.
