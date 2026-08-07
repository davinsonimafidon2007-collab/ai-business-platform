# ROI.1 (+ REC.1 relacionado) — DONE

Fecha: 2026-08-06

## Hecho

- [x] `app/services/profit_coherence.py` — `build_coherence_warnings`
- [x] `app/services/recommendation_labels.py` — risk + recommendation ES
- [x] Schema `ProfitAnalysisSchema`: `coherence_warnings`, `risk_label_es`, `recommendation_label_es`
- [x] Mapper `app/api/v1/routes/search.py` emite esos campos
- [x] OPP list: `recommendation_label_es` / `risk_label_es` en `OpportunityRead` + route
- [x] Tests: `test_profit_coherence.py`, `test_recommendation_labels.py`
- [x] Frontend types + VehicleDrawer consumen warnings/labels

## No reabrir

No reimplementar coherence/labels. No cambiar fórmulas de ROI en este task (ya cerrado).
