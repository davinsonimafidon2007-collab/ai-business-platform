# TODO: Fixes de Event Loop y Mejoras de Infraestructura

## FIX 1 - Eliminar bloqueo del Event Loop en ComparableMarketEstimator
- [ ] `comparable_market_estimator.py`: Eliminar `import asyncio`, `import concurrent.futures`
- [ ] `comparable_market_estimator.py`: Eliminar método `_run_async()`
- [ ] `comparable_market_estimator.py`: Hacer `estimate()` → `async def estimate()` 
- [ ] `comparable_market_estimator.py`: Eliminar `estimate_async()` (ahora `estimate()` es async)
- [ ] `market_estimator.py`: Cambiar `def estimate` → `async def estimate` en el Protocol

## FIX 2 - Actualizar SearchOrchestrator._analyze_vehicle()
- [ ] `search_orchestrator.py`: Simplificar llamada a `estimate()` (eliminar fallback `getattr`)

## FIX 3 - Eliminar segundo bridge async (verificar)
- [ ] `comparable_market_estimator.py`: Verificar que `_compute_and_cache` usa `await self._save_to_cache`

## FIX 4 - Eliminar except silencioso
- [ ] `search_orchestrator.py`: Importar logger y reemplazar `except Exception: continue/pass`
- [ ] `comparable_market_estimator.py`: Reemplazar `except Exception: continue` en `_search_comparables`

## FIX 5 - Eliminar print() en http_client.py
- [ ] Verificar que no hay `print()` en `http_client.py`

## FIX 6 - Construcción segura de URLs
- [ ] Verificar que `urljoin` ya está en `http_client.py` y `base.py`

## FIX 7 - Eliminar imports duplicados en vehicle_scorer.py
- [ ] Verificar y eliminar imports duplicados si existen

## Validación
- [ ] Verificar sintaxis de todos los archivos modificados
- [ ] Verificar que no quedan `ThreadPoolExecutor` ni `asyncio.run()` en el flujo
- [ ] Verificar que no quedan `print()` en `http_client.py`
- [ ] Verificar que todas las URLs usan `urljoin`
