# Auditoría — Testing / cobertura / deuda técnica
Fecha: 2026-08-20
Commit auditado: cc2a256a433d998531be578517b3abdaf1217996

## Hallazgos confirmados (con evidencia)
- `tests/unit/` tiene cobertura amplia; `tests/integration/` incluye health, search, vehicle, auth, users, searches, inspection, security, rbac, vision, database.
- `pyproject.toml` define `[tool.pytest.ini_options]` con `testpaths=["tests"]` y markers `fixture_provider` y `live_provider` en esta rama.
- Hallazgo TASK 27: existen asserts tipo `hasattr` sin comportamiento: `tests/integration/test_negotiation_integration.py:319-320`, `tests/integration/test_search_engine.py:259,343`, `tests/unit/test_comparable_market_estimator.py:760`, `tests/unit/test_evaluation_engine.py:354-367`, `tests/unit/test_opportunity_finder.py:362`, `tests/unit/test_profit_analyzer.py:189,268`, `tests/unit/test_search_orchestrator.py:348-352`, `tests/unit/test_vehicle_scorer.py:134-135`.
- Scripts de parcheo en raíz: `fix.bat`, `fix.js`, `frontend/fix_admin.mjs`, `frontend/apply-mobile-release-tasks.sh` no existen en el árbol actual.
- `ai-agent-platform/` no existe en el árbol actual.

## No verificado / requiere ejecución que este entorno no permite
- Cobertura real `pytest --cov=app --cov-report=term-missing` no ejecutada porque el entorno local carga `site-packages` del venv de Hermes y rompe importaciones antes de iniciar pytest. Se aisla como problema de entorno, no del código.

## Riesgos priorizados
| Riesgo | Severidad | Evidencia |
|---|---|---|
| Tests `hasattr` sin verificación de comportamiento | Media | múltiples archivos listados |
| Cobertura real desconocida | Media | no ejecutable en este entorno |
| Scripts parcheo ausentes ahora, pero históricamente commits | Baja | ausentes en checkout actual |
