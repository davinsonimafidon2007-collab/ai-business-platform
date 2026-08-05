# TASK J.1 — Alertas por racha de fallos de jobs (`consecutive_failures`)

## TODO Steps

- [x] FIX 1: `app/core/config.py` + `.env.example` — añadir 4 settings `JOB_FAILURE_ALERT_*`
- [x] FIX 2: Crear `app/services/job_failure_alert_service.py` (threshold + cooldown por job_name)
- [x] FIX 3: Hook en `app/jobs/scheduler.py` (`_run_periodic`) + DI en `Scheduler.__init__` + wiring en `factory.py`
- [x] FIX 4: Tests `tests/unit/test_job_failure_alert_service.py` (nuevo) + test integración en `test_scheduler.py`
- [x] Verificación: `pytest -q tests/unit/test_job_failure_alert_service.py tests/unit/test_scheduler.py tests/unit/test_jobs.py` → 53 passed
