"""Diagnostic runner: runs specific tests and dumps full tracebacks to a file.

Usage: python _diag_tests.py <output_file> <test_node_id> [<test_node_id>...]
"""
from __future__ import annotations

import contextlib
import os
import sys

# Must be set before importing app.main (which validates min length at import time)
os.environ["JWT_SECRET_KEY"] = "diag-secret-key-that-is-definitely-at-least-32-chars-long-1234567890"

import pytest

if __name__ == "__main__":
    output_file = sys.argv[1]
    node_ids = sys.argv[2:]
    args = ["-q", "--tb=long", "-p", "no:cacheprovider", *node_ids]
    ret = 0
    with open(output_file, "w", encoding="utf-8") as fh:
        with contextlib.redirect_stdout(fh), contextlib.redirect_stderr(fh):
            ret = pytest.main(args)
    print(f"pytest exit code: {ret}")
    sys.exit(ret)

