# TASK_A_06 — Eliminar tests sin comportamiento real

## Problema
Multiples tests solo comprueban existencia de atributos/metodos con
`hasattr`, sin ejercitar comportamiento ni verificar outputs.

## Archivos a modificar
- `tests/integration/test_negotiation_integration.py`
- `tests/integration/test_search_engine.py`
- `tests/unit/test_comparable_market_estimator.py`
- `tests/unit/test_evaluation_engine.py`
- `tests/unit/test_opportunity_finder.py`
- `tests/unit/test_profit_analyzer.py`
- `tests/unit/test_search_orchestrator.py`
- `tests/unit/test_vehicle_scorer.py`

## Accion
- Reescribir cada bloque para invocar la funcion y comprobar resultado.
- Si no se puede, eliminar el test ruidoso.

## Criterio de aceptacion
- Ningun test se limita a comprobar que una funcion existe sin ejecutarla.
