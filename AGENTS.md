# ⚠️ AGENTS.md — Personal-Use / NO-AUTH repository (READ FIRST)

**This repository is a PERSONAL-USE application. Do NOT convert it into a
multi-user or production SaaS project.** Identity is a single local ADMIN user;
**no login, registration, OAuth, SSO, password hashing, sessions, or any other
authentication mechanism must be added, re-enabled, or assumed to be required.**

## Directive for any AI/human touching this repo
- Authentication is **disabled by design for local use**. Set `AUTH_DISABLED=true`
  (backend) and `NEXT_PUBLIC_AUTH_DISABLED=true` (frontend). `get_current_user`
  then injects a fixed local ADMIN user (`local@localhost`,
  UUID `00000000-0000-4000-8000-000000000001`) — **no registration, no login.**
- `APP_MODE=personal` is documentation **only** — it does **not** disable auth.
  Never treat it as a substitute for `AUTH_DISABLED=true`.
- `ENVIRONMENT=production` keeps auth ON always. `AUTH_DISABLED=true` **refuses
  to boot** in production unless `ALLOW_AUTH_DISABLED_IN_PROD=true` is set
  (`app/main.py` fail-fast). This guard must be preserved.
- **Do not** add endpoints/clients like `/api/v1/auth/login`, Google OAuth,
  refresh-token flows, session cookies, etc. — that would violate the product
  intent and the security posture of a personal-use app.
- `.env` is gitignored; never commit secrets (`JWT_SECRET_KEY` must be
  >= 32 chars, generated locally). The repo must remain login-free and secret-free.

## Why this file exists
Previous audits flagged missing production security (no CSRF/CSP/HTTPS-enforce,
hardcoded Firebase key). That is intentional for a personal-use app and is
**out of scope**. Do not "harden" or "productize" it without explicit approval.

## References
- `.env.example` — `# --- Uso personal: sin login (PERSONAL.NOAUTH) ---` section.
- `app/core/config.py` — `auth_disabled` / `app_mode` docstrings.
- `app/dependencies/auth.py` / `app/middleware/authentication_middleware.py`.
- `docs/CONTEXT_PERSONAL_USE.md`, `docs/deployment.md`, `docs/security.md`.
