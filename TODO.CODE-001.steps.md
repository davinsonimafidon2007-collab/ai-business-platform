# TODO — CODE-001: Dead code, higiene y deuda técnica controlada

## Pasos
- [x] 1. Inventario: localizar dead code / artefactos
- [x] 2. Borrar paquetes vacíos muertos (`app/agents`, `app/orchestrator`, `app/tasks`, `app/telemetry`, `app/workers`)
- [x] 3. Borrar `app/__pycache__.zip` (untracked)
- [x] 4. Endurecer `.gitignore` (`*.zip`, `.mypy_cache/`, `*.egg-info/`, fixtures zip)
- [x] 5. Config ruff en `pyproject.toml` (`[tool.ruff.lint]`)
- [x] 6. Añadir `scripts/lint.ps1`
- [x] 7. Refactor seguro en `app/services/search_orchestrator.py` (extraer `_matches_filters`)
- [x] 8. Actualizar `TODO.md` (marcar CODE-001)
- [x] 9. Verificación: `ruff check app tests` + `pytest tests/unit -q`
