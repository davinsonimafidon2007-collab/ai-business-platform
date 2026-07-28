# TODO: Inspection Session Module — Integration Phase

## Backend Service
- [ ] `app/services/inspection_service.py` — Orchestrator service

## Backend API
- [ ] `app/api/v1/schemas/inspection.py` — Pydantic schemas
- [ ] `app/api/v1/routes/inspection.py` — REST endpoints
- [ ] `app/api/v1/router.py` — Register inspection router
- [ ] `app/api/v1/dependencies.py` — Add DI for InspectionService

## Frontend
- [ ] `frontend/src/app/types/inspection.ts` — TypeScript interfaces
- [ ] `frontend/src/app/services/inspection.ts` — API client
- [ ] `frontend/src/app/features/inspection/InspectionProgressBar.tsx`
- [ ] `frontend/src/app/features/inspection/CategoryStep.tsx`
- [ ] `frontend/src/app/features/inspection/InspectionSummary.tsx`
- [ ] `frontend/src/app/features/inspection/InspectionPage.tsx`
- [ ] `frontend/src/app/inspection/page.tsx`
- [ ] `frontend/src/app/inspection/[id]/page.tsx`
- [ ] `frontend/src/app/layout/sidebar.tsx` — Add nav item

## Tests
- [ ] `tests/unit/test_inspection_models.py`
- [ ] `tests/unit/test_inspection_service.py`
- [ ] `tests/integration/test_inspection_api.py`

## Final
- [ ] Run all tests
- [ ] Fix any errors
- [ ] Confirm everything compiles and tests pass
