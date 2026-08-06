# TODO — ROI.1: coherence_warnings en profit ✅

## Entregado
- [x] FIX 1: `app/services/profit_coherence.py` — `build_coherence_warnings` (mensajes ES, no bloqueante)
- [x] FIX 3: `ProfitAnalysisSchema.coherence_warnings` en `app/api/v1/schemas/common.py`
- [x] Mapper: compute + inyectar `coherence_warnings` en `app/api/v1/routes/search.py` (desde `pa` + `me.market_price`)
- [x] FIX 4: tests `tests/unit/test_profit_coherence.py` (9 tests) — verdes
- [x] Frontend type `coherence_warnings?` en `frontend/src/app/types/vehicle.ts`
- [x] Drawer: lista de avisos en Profit (`VehicleDrawer.tsx`) — amber, no bloqueante
- [x] `TODO.md` entrada ROI.1
- [x] Verificación: `release_check --skip-smoke` + pytest unit

## Alcance
- [x] No se cambió ninguna fórmula de profit/ROI (solo capa de aviso).
- [x] No se tocaron scrapers, scoring/opportunity umbrales, Redis/Compose ni proxy.
- [ ] (ops) Afinar umbrales con fixtures reales de profit si saltan warnings siempre.

## Verificación
```powershell
$env:ENVIRONMENT="test"
$env:JWT_SECRET_KEY="test_secret_key_that_is_at_least_32_characters_long_1234567890"
python -m pytest tests/unit/test_profit_coherence.py -q   # 9 passed
python scripts/release_check.py --skip-smoke
```

