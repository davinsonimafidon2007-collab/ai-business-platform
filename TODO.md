# Plan Task E.2 — Guardar última simulación en el deal

## Pasos
- [x] 1. Explorar backend: modelo Deal, schemas, service, API, repo
- [x] 2. Explorar frontend: SimulateProfitPanel, opportunities, deals page, services, tests
- [x] 3. Confirmar plan con el usuario (aprobado)
- [x] 4. Backend: añadir columnas `last_sim_*` al modelo `Deal`
- [x] 5. Backend: nueva migración Alembic (down_revision = e2f3a4b5c6d7)
- [x] 6. Backend: schemas `DealSimulationUpdate` + campos `last_sim_*` en `DealRead`
- [x] 7. Backend: `DealService.save_simulation()` (ownership + no tocar status)
- [x] 8. Backend: endpoint `PATCH /deals/{id}/simulation`
- [x] 9. Frontend: `updateDealSimulation()` + campos `last_sim_*` en `deals.ts`
- [x] 10. Frontend: `SimulateProfitPanel` con prop `dealId` y botón "Guardar en deal"
- [x] 11. Frontend: `opportunities/page.tsx` — pasar dealId al panel (Map de deals activos)
- [x] 12. Frontend: `deals/page.tsx` — mostrar última simulación en la card
- [x] 13. Tests backend: `test_deal_service.py` + `test_deals_api.py`
- [x] 14. Tests frontend: `deals.test.ts` (updateDealSimulation)
- [x] 15. Build + tests + commit
