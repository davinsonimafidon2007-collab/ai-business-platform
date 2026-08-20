# Auditoría — DevOps / CI / Docker
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `docker-compose.yml` — expone `15432:5432` y `16379:6379` al host.
- Redis auth **no activada por defecto** en `docker-compose.yml` en el momento de la auditoría inicial del repo; posteriormente se agregó configuración con `REDIS_PASSWORD` y `requirepass`, pero requiere verificación de `docker compose config` tras esos cambios.
- `.github/workflows/` **no existe** en este checkout; no hay CI definida en el árbol actual.
- `docker-compose.logging.yml` no existe en el checkout.
- `Dockerfile` expone 8000, usa `uv sync --group dev`.
- `frontend/Dockerfile` no existe.
- `.dockerignore` incluye `.env`, `.venv`, `__pycache__`, `htmlcov`, `.coverage`. No incluye `node_modules`, lo que puede enviar dependencias frontend al contexto Docker.

## No verificado / requiere ejecución que este entorno no permite
- Estado real del último run de workflows porque no existe `.github/workflows/` en el checkout.
- `docker compose up -d --build` limpio completo se ejecutó parcialmente durante la sesión; no se pegó log completo aquí por scope.
- `gitleaks`/`npm audit`/`pip-audit` no están presentes en CI en este checkout.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| `.github/workflows/` ausente | Alta | listado de repo sin `.github` |
| `.dockerignore` sin `node_modules` | Media | `.dockerignore` |
| Puertos DB/Redis expuestos sin auth previa | Media | `docker-compose.yml` |
| `frontend/Dockerfile` ausente | Baja | listado de repo |
