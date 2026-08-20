# TASK_A_03 — Corregir modo fixture ES roto

## Problema
`app/providers/registry.py` registra `es_market_fixture`,
`coches_net_fixture` y `coches_net_html_fixture`, pero esos archivos
no existen en disco. Con `ES_DATA_MODE=fixture` el pipeline ES
queda inhabilitado en runtime.

## Archivos a modificar
- `app/providers/registry.py`
- `app/providers/es_market_fixture.py` (nuevo)
- `app/providers/coches_net_fixture.py` (nuevo)
- `app/providers/coches_net_html_fixture.py` (nuevo)

## Accion
- Crear las clases fixture faltantes heredando de `VehicleProvider`.
- O, si se prefiere eliminar modo fixture, borrar los `ensure_*` y
  forzar `live` con fail-fast explicito.

## Criterio de aceptacion
- `ES_DATA_MODE=fixture` arranca y registra providers sin ImportError.
- `ES_DATA_MODE=live` registra `coches_net` real.
