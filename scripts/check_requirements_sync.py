"""Fail if requirements.txt is out of sync with uv export (Task C.1)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"


def export_runtime() -> str:
    r = subprocess.run(
        [
            "uv",
            "export",
            "--no-hashes",
            "--no-dev",
            "--no-emit-project",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


def normalize(text: str) -> list[str]:
    """Strip GENERATED header comments and blank lines; keep package pins."""
    lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return sorted(lines)


def main() -> int:
    if not REQ.is_file():
        print("ERROR: requirements.txt missing", file=sys.stderr)
        return 1
    try:
        generated = export_runtime()
    except FileNotFoundError:
        print("ERROR: uv not found in PATH", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print(e.stderr or e.stdout, file=sys.stderr)
        return 2

    current = normalize(REQ.read_text(encoding="utf-8"))
    expected = normalize(generated)
    if current == expected:
        print("OK: requirements.txt in sync with uv export")
        return 0

    missing = set(expected) - set(current)
    extra = set(current) - set(expected)
    print("ERROR: requirements.txt out of sync with uv export", file=sys.stderr)
    if missing:
        print("  missing in requirements.txt:", file=sys.stderr)
        for x in sorted(missing):
            print(f"    + {x}", file=sys.stderr)
    if extra:
        print("  extra in requirements.txt:", file=sys.stderr)
        for x in sorted(extra):
            print(f"    - {x}", file=sys.stderr)
    print(
        "\nFix: run scripts/export_requirements.ps1 (or uv export … -o requirements.txt)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

