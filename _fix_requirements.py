"""One-off script: add missing deps to requirements.txt preserving UTF-16 LE BOM.

Reads requirements.txt as utf-16 (auto-detects BOM), inserts the two missing
dependency lines in alphabetical order, and writes back as utf-16 (Python's
'utf-16' codec writes a LE BOM by default).
"""

from __future__ import annotations

import pathlib

REQ_PATH = pathlib.Path("requirements.txt")

NEW_LINES = [
    "aiosmtplib>=3.0.0,<4.0.0",
    "firebase-admin>=6.0.0,<7.0.0",
]


def main() -> None:
    raw = REQ_PATH.read_bytes()
    has_bom = raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff")
    text = raw.decode("utf-16")

    lines = text.splitlines()
    # Normalize line endings while preserving them on write (splitlines strips them).
    # We re-join with the original line terminator style.
    terminator = "\r\n" if "\r\n" in text else "\n"

    missing = [d for d in NEW_LINES if d.split(">=")[0].split("==")[0] not in text]
    print("Missing before:", missing)

    for dep in NEW_LINES:
        name = dep.split(">=")[0].split("==")[0].lower()
        if any(line.split(">=")[0].split("==")[0].lower() == name for line in lines):
            print(f"Already present: {dep}")
            continue
        # Find insertion index keeping alphabetical order (case-insensitive).
        idx = 0
        for i, line in enumerate(lines):
            if line.strip() == "":
                continue
            line_name = line.split(">=")[0].split("==")[0].lower()
            if line_name < name:
                idx = i + 1
            else:
                break
        lines.insert(idx, dep)
        print(f"Inserted at index {idx}: {dep}")

    new_text = terminator.join(lines) + terminator
    new_bytes = new_text.encode("utf-16")  # writes LE BOM by default

    REQ_PATH.write_bytes(new_bytes)

    # Verification
    verify = REQ_PATH.read_bytes()
    print("BOM now:", verify[:4].hex())
    decoded = verify.decode("utf-16")
    print("Has aiosmtplib:", "aiosmtplib" in decoded)
    print("Has firebase-admin:", "firebase-admin" in decoded)
    print("Lines:", len(decoded.splitlines()))
    print("Was BOM originally:", has_bom)


if __name__ == "__main__":
    main()

