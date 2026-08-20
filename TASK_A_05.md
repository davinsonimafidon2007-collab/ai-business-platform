# TASK_A_05 — Endurecer dockerignore y compose

## Problema
`.dockerignore` no excluye `node_modules/`, y `docker-compose.yml`
expone puertos de BD/Redis sin auth previa en la version base.

## Archivos a modificar
- `.dockerignore`
- `docker-compose.yml`

## Accion
- Anadir `node_modules/` a `.dockerignore`.
- Revisar exposition de `15432` y `16379`; mantener solo si es necesario
  para desarrollo, documentar riesgo en README.

## Criterio de aceptacion
- Contexto Docker no incluye `node_modules`.
- Puertos expuestos estan documentados y justificados.
