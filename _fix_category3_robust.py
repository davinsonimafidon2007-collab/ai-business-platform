"""Robust fix for Category 3 remaining files.

Diagnoses and fixes:
  1. tests/unit/test_inspection_service.py — create_session now requires user_id
  2. tests/integration/database/test_opportunity_repository.py — Vehicle requires user_id in test_list_returns_paginated
"""

from __future__ import annotations

from pathlib import Path


def diagnose() -> None:
    p = Path("tests/unit/test_inspection_service.py")
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if "create_session" in line:
            print(f"[inspection:{i}] {line!r}")

    p2 = Path("tests/integration/database/test_opportunity_repository.py")
    for i, line in enumerate(p2.read_text(encoding="utf-8").splitlines(), 1):
        if "Vehicle(" in line or "source=" in line and "ext_" in line:
            print(f"[opportunity:{i}] {line!r}")
        if "external_id=f" in line:
            print(f"[opportunity:{i}] {line!r}")


def fix_inspection() -> None:
    p = Path("tests/unit/test_inspection_service.py")
    lines = p.read_text(encoding="utf-8").splitlines()
    changed = False
    for i, line in enumerate(lines):
        if "service.create_session(created.vehicle_id)" in line and "user_id" not in line:
            lines[i] = line.replace(
                "service.create_session(created.vehicle_id)",
                'service.create_session(created.vehicle_id, user_id="00000000-0000-0000-0000-000000000099")',
            )
            changed = True
    # Add assertion after the DRAFT status assertion (only once)
    new_lines: list[str] = []
    added_assert = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        if (
            not added_assert
            and 'call_args.args[0].status == "DRAFT"' in line
            and "user_id" not in new_lines[-1]
        ):
            new_lines.append('    assert repos[0].create.call_args.args[0].user_id == "00000000-0000-0000-0000-000000000099"')
            added_assert = True
    if changed or added_assert:
        p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"UPDATED inspection: changed={changed} added_assert={added_assert}")
    else:
        print("NO CHANGE inspection")


def fix_opportunity() -> None:
    p = Path("tests/integration/database/test_opportunity_repository.py")
    lines = p.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    changed = False
    for i, line in enumerate(lines):
        if line.strip() == 'source="test",' and "user_id" not in new_lines[-1]:
            # Ensure we are inside a Vehicle( constructor
            # Look back up to 5 lines for 'Vehicle(' at class level
            window = "\n".join(new_lines[-5:])
            if "Vehicle(" in window:
                indent = line[: len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}user_id="00000000-0000-0000-0000-000000000099",')
                changed = True
        new_lines.append(line)
    if changed:
        p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"UPDATED opportunity: changed={changed}")
    else:
        print("NO CHANGE opportunity")


if __name__ == "__main__":
    diagnose()
    fix_inspection()
    fix_opportunity()
    print("DONE")

