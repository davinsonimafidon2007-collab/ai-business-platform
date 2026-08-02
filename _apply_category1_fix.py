"""Apply Category 1 fix: prefix /auth routes with /api/v1 in the three auth test files."""

from pathlib import Path

FILES = [
    "tests/integration/test_security_api.py",
    "tests/integration/test_auth_api.py",
    "tests/integration/test_password_reset_api.py",
]

for rel in FILES:
    p = Path(rel)
    text = p.read_text(encoding="utf-8")
    original = text
    # Replace any "/auth/..." path literal used in client calls with "/api/v1/auth/..."
    text = text.replace('"/auth/', '"/api/v1/auth/')
    if text != original:
        p.write_text(text, encoding="utf-8")
        print(f"UPDATED {rel}")
    else:
        print(f"NO CHANGE {rel}")

