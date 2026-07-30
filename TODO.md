# Fix Plan - Make Project Functional

## Cycle 1: Database Unification
- [ ] Fix `app/db/session.py` to use `DatabaseManager` (single engine)
- [ ] Fix `app/database/manager.py` to remove `Base.metadata.create_all` (Alembic handles migrations)
- [ ] Fix `main.py` to use shared `DatabaseManager` from `app/db/session.py`

## Cycle 2: Environment Configuration
- [ ] Create `.env.example` with all required variables

## Cycle 3: Verify & Test
- [ ] Verify all imports resolve correctly
- [ ] Run tests to check for regressions
- [ ] Verify application starts without errors
