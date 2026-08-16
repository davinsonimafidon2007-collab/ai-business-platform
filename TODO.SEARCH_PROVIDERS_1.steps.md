# TODO — SEARCH.PROVIDERS.1: filtro comparable_providers

Objetivo: permitir restringir (o fijar por settings) qué sources usan los
comparables del estimador de mercado, sin cambiar el default actual (todo el
registry). 100 % backward-compatible.

- [ ] FIX 0 — Baseline verde (test_comparable_market_estimator + test_market_estimation_schema)
- [ ] FIX 1 — Settings: `comparable_providers` + `COMPARABLE_PROVIDERS` en `.env.example`
- [ ] FIX 1b — Helper `resolve_comparable_provider_names` (request > settings > all; intersección con registry)
- [ ] FIX 2 — `estimate(..., comparable_providers=)` y propagación a `_search_comparables`
- [ ] FIX 3 — `SearchAPIRequest.comparable_providers` opcional + cableado search → analyzer → estimate
- [ ] FIX 4 — Unit tests `test_comparable_provider_filter.py` (+ integración ligera del estimador)
- [ ] FIX 5 — Docs (TODO checklist + README/HANDOFF una línea)
- [ ] Verificación: `python -m pytest -q tests/unit/test_comparable_provider_filter.py tests/unit/test_comparable_market_estimator.py -q`
- [ ] Verificación: `python scripts/release_check.py --skip-smoke`

