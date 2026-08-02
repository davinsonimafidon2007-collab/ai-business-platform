"""Apply Category 2 fix for test_comparable_market_estimator.py (idempotent).

Converts all test methods in TestComparableMarketEstimator that call
``estimator.estimate(...)`` to async (``@pytest.mark.asyncio`` + ``async def``
+ ``await``), since ComparableMarketEstimator.estimate is now a coroutine.
Also repairs any misplaced @pytest.mark.asyncio decorator at column 0.
Safe to run multiple times (no duplicate markers / awaits).
"""

from __future__ import annotations

import re
from pathlib import Path

PATH = Path("tests/unit/test_comparable_market_estimator.py")
text = PATH.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

out: list[str] = []
in_target_class = False
i = 0

# Regex allows return annotation: def test_x(...) -> None:
METHOD_RE = re.compile(r"^( {4})(async )?def (test_[\w]+)\(.*\)( -> .*)?:\n$")

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # Detect entry into target class
    if re.match(r"^class TestComparableMarketEstimator\b", line):
        in_target_class = True
        out.append(line)
        i += 1
        continue

    if in_target_class:
        # A misplaced top-level (col 0) decorator inside the class: repair to 4-space indent
        if stripped.startswith("@pytest.mark.asyncio") and not line.startswith("    "):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and re.match(r"^    (async )?def ", lines[j]):
                out.append("    @pytest.mark.asyncio\n")
                i += 1
                continue

        # Detect exit from class: any top-level (non-indented) non-blank, non-decorator line
        if stripped and not line[0].isspace() and not stripped.startswith("@"):
            in_target_class = False
            out.append(line)
            i += 1
            continue

        m = METHOD_RE.match(line)
        if m:
            indent = m.group(1)
            is_async_def = bool(m.group(2))
            method_name = m.group(3)

            # Collect body lines: blank lines or lines indented >= 8 spaces
            j = i + 1
            body: list[str] = []
            while j < len(lines):
                b = lines[j]
                if b.strip() == "":
                    body.append(b)
                    j += 1
                    continue
                b_indent = len(b) - len(b.lstrip(" "))
                if b_indent >= 8:
                    body.append(b)
                    j += 1
                    continue
                break

            body_text = "".join(body)
            if "estimator.estimate(" in body_text:
                # Avoid duplicate marker if previous line is already the marker
                already_marked = bool(out) and out[-1] == f"{indent}@pytest.mark.asyncio\n"
                if not already_marked:
                    out.append(f"{indent}@pytest.mark.asyncio\n")
                if not is_async_def:
                    line = line.replace("def ", "async def ", 1)
                out.append(line)
                i += 1
                # Rewrite the body: add await before estimator.estimate(...) calls
                for b in body:
                    if "= estimator.estimate(" in b and "= await estimator.estimate(" not in b:
                        b = b.replace("= estimator.estimate(", "= await estimator.estimate(")
                    out.append(b)
                i = j
                continue

    out.append(line)
    i += 1

new_text = "".join(out)
PATH.write_text(new_text, encoding="utf-8")

count_async = new_text.count("    @pytest.mark.asyncio\n")
count_await = new_text.count("= await estimator.estimate(")
compile(new_text, str(PATH), "exec")
print(f"OK: asyncio markers: {count_async}")
print(f"OK: await estimator.estimate calls: {count_await}")

