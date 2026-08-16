# TODO — TASK P3-002 (DEVOPS-001): Health compuesto + backups + observabilidad mínima

## Objetivo
Pasar de "health OK cosmético" a operabilidad básica de producción temprana sin
forzar stack Prometheus/Grafana.

## Pasos
- [x] 1. `app/api/v1/schemas/health.py` — extender `HealthResponse` con `checks`.
- [x] 2. `app/api/v1/routes/health.py` — health compuesto async (DB `SELECT 1` con
         timeout corto + Redis `PING`); HTTP 503 solo si DB falla.
- [x] 3. `app/main.py` — eliminar handler `/health` duplicado (dejar solo el del router).
- [x] 4. `scripts/backup_postgres.sh` — normaliza `DATABASE_URL` (quita `+asyncpg`),
         `pg_dump -Fc` → `backups/`, retention N=7.
- [x] 5. `scripts/restore_postgres.sh` — `pg_restore` con confirmación o `--force`.
- [x] 6. `.gitignore` — añadir `backups/`.
- [x] 7. `docker-compose.obs.yml` — Prometheus/Grafana con `profiles: [obs]`
         (no se inicia con `compose up` por defecto).
- [x] 8. `app/telemetry/__init__.py` — placeholder de telemetry (phase 2).
- [x] 9. `docs/ops.md` — health contract, backup/restore runbook, logging/request_id,
         job failure alerts, observabilidad phase 2.
- [x] 10. `.env.example` — vars de backup (`BACKUP_RETENTION`, `BACKUP_DIR`).
- [x] 11. `tests/unit/test_health.py` — matriz ok/degraded/error (+ disabled redis).
- [x] 12. `tests/integration/api/test_health_api.py` — health compuesto real (200 + checks).
- [x] 13. `README.md` — link a `docs/ops.md`.
- [x] 14. `TODO.md` — sección TASK P3-002 resumen.
- [x] 15. Verificación: `uv run pytest tests/unit/test_health.py tests/unit/test_logging_middleware.py -q`,
         luego `uv run pytest tests/unit -q`.
