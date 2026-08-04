# Task D.3 — Deals: sin duplicados activos + `offer_price` al pasar a OFFER

## Steps
- [x] 1. Explorar backend deals API y frontend deals/opportunities
- [x] 2. Backend: `deal_repository.get_active_by_opportunity` + filtro `opportunity_id` en `list_for_user`
- [x] 3. Backend: `deal_service.create` bloquea deal activo (409) + `list` filtra por opportunity
- [x] 4. Backend: `GET /deals?opportunity_id=` en `app/api/v1/deals.py`
- [x] 5. Tests backend: `test_deal_service.py` (duplicado 409, tras terminal permitido)
- [x] 6. Tests backend: `test_deals_api.py` (409 create, PATCH OFFER con offer_price)
- [x] 7. FE: `deals.ts` añade `opportunity_id` a filtros
- [x] 8. FE: `deals/page.tsx` pide `offer_price` al pasar a OFFER
- [x] 9. FE: `opportunities/page.tsx` maneja 409/422 con mensaje "Ya tienes un deal abierto" + link a /deals
- [x] 10. Verificar: `pytest` backend (19 passed) + `npm run build` frontend (OK, /deals y /opportunities generados)
- [x] 11. Commit (99e46f6) + push origin/main
