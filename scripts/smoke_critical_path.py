"""Smoke E2E API — camino crítico (Task E2E.1) + oportunidades + admin (Task E2E.2).

Uso:
  set BASE_URL=http://localhost:8000
  set JWT_SECRET_KEY=...   # solo si levantas la app en el mismo proceso (no hace falta para HTTP)
  python scripts/smoke_critical_path.py
  python scripts/smoke_critical_path.py --with-opportunities
  python scripts/smoke_critical_path.py --with-admin
  # --with-admin requiere credenciales ADMIN y valida también el bloque providers:
  #   SMOKE_ADMIN_EMAIL / SMOKE_ADMIN_PASSWORD  o  --admin-email/--admin-password

Exit 0 = OK; 1 = fallo de aserción/HTTP; 2 = setup (API caída).

Sin flags se conserva exactamente el camino crítico de E2E.1 (regresión safe).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
EMAIL = f"smoke_{uuid.uuid4().hex[:10]}@example.com"
PASSWORD = "SmokeTest123!"


def die(code: int, msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke E2E API (crítico + opportunidades + admin)")
    parser.add_argument(
        "--with-opportunities",
        action="store_true",
        help="Además del camino crítico, GET /opportunities?limit=5 debe responder 200.",
    )
    parser.add_argument(
        "--with-admin",
        action="store_true",
        help="Además del camino crítico, valida GET /admin/status con un user ADMIN.",
    )
    parser.add_argument("--admin-email", default=os.environ.get("SMOKE_ADMIN_EMAIL"))
    parser.add_argument("--admin-password", default=os.environ.get("SMOKE_ADMIN_PASSWORD"))
    return parser.parse_args()


def check_opportunities(c: httpx.Client) -> None:
    """GET /opportunities?limit=5 — 200 aunque la lista esté vacía."""
    r = c.get("/opportunities", params={"limit": 5})
    if r.status_code != 200:
        die(1, f"GET /opportunities?limit=5 → {r.status_code} {r.text[:300]}")
    data = r.json()
    total = data.get("total")
    print(f"OK: opportunities list → 200 (total={total})")
    items = data.get("items") or []
    if total is not None and total > 0:
        if not isinstance(items, list) or "id" not in (items[0] or {}):
            die(1, "opportunities con total>0 pero primer item sin id")


def check_admin(c: httpx.Client, args: argparse.Namespace) -> None:
    """Login como ADMIN y GET /admin/status — 200 con claves redis_ok/canary/jobs/providers."""
    admin_email = args.admin_email
    admin_password = args.admin_password
    if not admin_email or not admin_password:
        die(
            2,
            "--with-admin requiere credenciales ADMIN "
            "(SMOKE_ADMIN_EMAIL/SMOKE_ADMIN_PASSWORD o --admin-email/--admin-password)",
        )

    login = c.post("/auth/login", json={"email": admin_email, "password": admin_password})
    if login.status_code not in (200, 201):
        die(1, f"admin login → {login.status_code} {login.text[:200]}")
    token = login.json().get("access_token") or login.json().get("accessToken")
    if not token:
        die(1, "admin login sin access_token")

    # Cliente aislado para no pisar el header del usuario smoke.
    with httpx.Client(base_url=API, timeout=30.0) as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        status = ac.get("/admin/status")
        if status.status_code in (401, 403):
            die(1, f"GET /admin/status → {status.status_code} (credenciales malas o no ADMIN)")
        if status.status_code != 200:
            die(1, f"GET /admin/status → {status.status_code} {status.text[:300]}")
        body = status.json()
        try:
            assert_admin_status_body(body)
        except AssertionError as exc:
            die(1, str(exc))
        jobs = body.get("jobs") or []
        canary = body.get("canary") or {}
        providers = body.get("providers") or {}
        registered = providers.get("providers") or providers.get("registered") or []
        profile = providers.get("default_import_cost_profile")
        print(
            f"OK: admin/status → 200 (redis_ok={body.get('redis_ok')}, "
            f"jobs={len(jobs)}, canary.success={canary.get('success')}, "
            f"providers.registered={registered!r}, providers.profile={profile!r})"
        )


def assert_admin_status_body(body: dict) -> None:
    """Validate /admin/status response body (pure, raises AssertionError).

    Asegura que el body contiene las claves requeridas por el smoke y que
    el bloque `providers` cumple el schema `ProvidersStatus` del admin.
    """
    for key in ("redis_ok", "canary", "jobs", "providers"):
        if key not in body:
            raise AssertionError(f"admin/status sin clave '{key}'")
    providers = body.get("providers") or {}
    if not isinstance(providers, dict):
        raise AssertionError("admin/status providers no es objeto")
    registered = providers.get("providers") or providers.get("registered")
    if registered is not None and not isinstance(registered, list):
        raise AssertionError("admin/status providers.list no es lista")


def main() -> None:
    args = parse_args()
    try:
        r = httpx.get(f"{BASE}/health", timeout=5.0)
    except httpx.HTTPError as e:
        die(2, f"API no responde en {BASE}: {e}")
    if r.status_code != 200:
        die(2, f"/health → {r.status_code}")

    # El client autenticado del usuario smoke se mantiene abierto para el
    # camino crítico y, si se pide, para el chequeo de opportunities (que
    # requiere el mismo token USER).
    with httpx.Client(base_url=API, timeout=30.0) as c:
        # Register (ignore 409 si ya existe)
        reg = c.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
        if reg.status_code not in (200, 201, 409):
            die(1, f"register → {reg.status_code} {reg.text[:200]}")

        login = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if login.status_code != 200:
            die(1, f"login → {login.status_code} {login.text[:200]}")
        token = login.json().get("access_token") or login.json().get("accessToken")
        if not token:
            die(1, "login sin access_token")
        c.headers["Authorization"] = f"Bearer {token}"

        me = c.get("/auth/me")
        if me.status_code != 200:
            die(1, f"/auth/me → {me.status_code}")

        # Vehicle mínimo (campos obligatorios de VehicleCreate: source,
        # external_id, brand, model; el resto del body es opcional).
        veh_body = {
            "brand": "BMW",
            "model": "320d",
            "year": 2020,
            "mileage": 50000,
            "price": 18000,
            "source": "smoke",
            "external_id": f"smoke-{uuid.uuid4().hex[:8]}",
        }
        veh = c.post("/vehicles", json=veh_body)
        if veh.status_code not in (200, 201):
            die(1, f"POST /vehicles → {veh.status_code} {veh.text[:300]}")
        vehicle_id = veh.json().get("id")
        if not vehicle_id:
            die(1, "vehicle sin id")

        deal = c.post("/deals", json={"vehicle_id": vehicle_id})
        if deal.status_code not in (200, 201):
            die(1, f"POST /deals → {deal.status_code} {deal.text[:300]}")
        deal_id = deal.json()["id"]

        sim = c.patch(
            f"/deals/{deal_id}/simulation",
            json={
                "purchase_price": 17000,
                "estimated_sale_price": 22000,
                "total_cost": 19000,
                "net_profit": 3000,
                "roi_percentage": 15.0,
                "profile_name": "SPAIN",
            },
        )
        if sim.status_code != 200:
            die(1, f"PATCH simulation → {sim.status_code} {sim.text[:300]}")

        # Transición a OFFER: el pipeline exige NEW -> CONTACTED -> OFFER.
        # Si el estado ya permite CONTACTED -> OFFER directo, el primer PATCH
        # a CONTACTED puede devolver 422 (si ya estuviera en CONTACTED); aquí
        # partimos de NEW así que debe aplicarse.
        st = c.patch(
            f"/deals/{deal_id}/status",
            json={"status": "CONTACTED"},
        )
        if st.status_code not in (200, 422):
            die(1, f"status CONTACTED → {st.status_code} {st.text[:200]}")

        offer = c.patch(
            f"/deals/{deal_id}/status",
            json={"status": "OFFER", "offer_price": 17000},
        )
        if offer.status_code != 200:
            die(1, f"status OFFER → {offer.status_code} {offer.text[:300]}")
        body = offer.json()
        if body.get("status") not in ("OFFER", "Offer"):
            die(1, f"status esperado OFFER, got {body.get('status')}")
        if body.get("offer_price") is None:
            die(1, "offer_price vacío tras OFFER")

        listed = c.get("/deals", params={"status": "OFFER"})
        if listed.status_code != 200:
            die(1, f"GET deals → {listed.status_code}")
        items = listed.json().get("items") or listed.json()
        if isinstance(items, dict):
            items = items.get("items", [])
        ids = {d.get("id") for d in items}
        if deal_id not in ids:
            die(1, "deal OFFER no listado en GET /deals?status=OFFER")

        # Extensión E2E.2 (opt-in): GET /opportunities con el token del
        # usuario smoke (el endpoint exige auth). Se hace aquí, dentro del
        # mismo client autenticado.
        if args.with_opportunities:
            check_opportunities(c)

    if args.with_admin:
        with httpx.Client(base_url=API, timeout=30.0) as c:
            check_admin(c, args)

    print("OK: smoke critical path passed")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
