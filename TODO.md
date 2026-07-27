# Security Layer Implementation - TODO

## Phase 1: Models & Database
- [x] `app/models/api_key.py` - ApiKey model (id, user_id, name, key_hash, prefix, scopes, description, expires_at, created_at, last_used_at, is_active)
- [x] `app/models/audit_log.py` - AuditLog model (id, user_id, action, resource, resource_id, details, ip_address, user_agent, timestamp) - immutable (create/read only)
- [x] Alembic migration for new tables (`alembic/versions/e1f2a3b4c5d6_add_api_keys_and_audit_logs.py`)

## Phase 2: Repositories
- [x] `app/repositories/api_key_repository.py` - CRUD for API keys
- [x] `app/repositories/audit_log_repository.py` - Create and query audit logs (no update/delete)

## Phase 3: Services
- [x] `app/services/api_key_service.py` - Generate keys with `abp_live_` prefix, hash storage, validate, show once
- [x] `app/services/audit_service.py` - Log all audit events (login, logout, refresh, API key usage, failed attempts, searches, critical changes)
- [x] `app/services/permission_service.py` - Dict-based ROLE_PERMISSIONS with can_search(), can_manage_users(), can_manage_api_keys(), can_view_admin()

## Phase 4: Middleware
- [x] `app/middleware/authentication_middleware.py` - Unified auth middleware (JWT Bearer OR API Key)
- [x] `app/middleware/rate_limit_middleware.py` - Rate limiting by IP, JWT subject, API Key, endpoint with role-based limits

## Phase 5: Configuration
- [x] `app/core/config.py` - Add api_key_prefix, api_key_length, rate_limit_premium, rate_limit_user, rate_limit_readonly, audit_retention_days

## Phase 6: Dependencies
- [x] `app/dependencies/auth.py` - Enhance with API key support, permission-based access control

## Phase 7: OpenAPI
- [x] `app/main.py` - Update FastAPI app with security schemes (Bearer + API Key Header)

## Phase 8: Tests
- [x] `tests/unit/test_api_key_service.py` - API key generation, hashing, validation, scopes
- [x] `tests/unit/test_audit_service.py` - Audit logging for all event types
- [x] `tests/unit/test_permission_service.py` - Role-based permission checks
- [x] `tests/unit/test_authentication_middleware.py` - Auth middleware (JWT + API Key)
- [x] `tests/unit/test_rate_limit_middleware.py` - Rate limiting by IP, user, API key, endpoint
- [x] `tests/integration/test_security_api.py` - Full integration tests

## Key Requirements
- ✅ No existing code modified - all security added as new files/layers
- ✅ Role enum UNCHANGED (ADMIN, USER only)
- ✅ No Permission model - simple dict-based PermissionService
- ✅ 2 middlewares only: AuthenticationMiddleware + RateLimitMiddleware
- ✅ API Keys with `abp_live_` prefix, shown once, stored as hash
- ✅ API Key revocation via is_active (not deleted)
- ✅ Audit logs immutable (create/read only)
- ✅ JWT and Refresh Token continue working exactly as before
- ✅ API Key auth is additional mechanism, not replacing existing flow
