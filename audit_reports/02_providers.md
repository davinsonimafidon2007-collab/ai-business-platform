# Auditoría — Providers / integraciones externas
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `mobile_de.py:18` y `mobile_de.py:45` — provider HTTP real (`BASE_URL=https://www.mobile.de`).
- `autoscout24.py:20` y `autoscout24.py:72` — provider HTTP real (`BASE_URL=https://www.autoscout24.de`).
- `coches_net.py:21` y `coches_net.py:32` — provider HTTP real (`BASE_URL=https://www.coches.net`).
- Fixtures referenciadas desde `registry.py:90-107` — `coches_net_fixture`, `coches_net_html_fixture`, `es_market_fixture` se importan en `TYPE_CHECKING` y se registran por `ensure_*`, pero **estos archivos no existen en `app/providers/`**. Si `ES_DATA_MODE=fixture`, la importación se salta en runtime y el modo fixture no funciona.
- `registry.py:110-146` — `ensure_default_providers()` respeta `ES_DATA_MODE`: fixture registra fixtures; live registra `coches_net` real. Fallo: usa `settings` importado en runtime; si `es_data_mode` se cambia tras import, no se reevalúa.
- `base.py:111-129` — `search()` incluye circuit breaker y captura `httpx.HTTPStatusError`, incluyendo 403; sin fallback silencioso.
- `http_client.py:207-228` — 403 registra fallo en circuit breaker y re-lanza excepción explícita; no hay fallback a fixture.
- `vision_provider.py:21-38` — mock explícito documentado como proveedor simulado local.

## No verificado / requiere ejecución que este entorno no permite
- No se puede ejecutar una búsqueda real contra `mobile.de`/`autoscout24`/`coches.net` desde CI para confirmar HTML/captcha actual.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| Fixtures ES ausentes en disco | Alta | `registry.py:90-107` |
| ES_DATA_MODE no reevaluable en runtime | Media | `registry.py:119` |
| Falta coverage/validación de `es_data_mode=fixture` | Media | archivos `.py` no existen |
| `AUTH_DISABLED` no mencionado aquí | Baja | fuera de scope providers |
