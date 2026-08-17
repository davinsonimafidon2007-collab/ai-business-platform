"""Shared pagination/listing limits (PERF-001).

Central place for server-side caps applied defensively at both the API layer
(Query validation) and the repository layer (deep defense), so a client that
asks for a huge ``limit`` is either rejected early (422) or silently capped at
the repository.
"""

from __future__ import annotations

from typing import Any

MAX_LIST_LIMIT = 100
"""Hard cap for every paginated listing (vehicles, deals, opportunities,
searches). Clients may not request more than this."""

DEFAULT_LIST_LIMIT = 20
"""Default page size used when the endpoint does not specify one."""

MAX_LIST_DEPTH = 5000
"""Hard cap for pagination depth (``skip``/offset) on every listing.

Without it, a client could request ``skip=999999`` and force a deep OFFSET
scan (slow on Postgres). Values beyond this are rejected at the API layer
(422) and clamped at the repository layer (deep defense).
"""

MAX_SEARCH_RESULTS = 100
"""Hard cap for ``max_results`` in search requests and search-order filters.
Mirrors the ``le=100`` validator of ``SearchRequest.max_results``."""


def clamp_limit(limit: Any, maximum: int = MAX_LIST_LIMIT) -> int:
    """Return ``limit`` clamped to ``[1, maximum]``.

    Defensive helper for repositories: even if a caller bypasses API
    validation (or passes a bogus value), the query never exceeds ``maximum``.
    """
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return maximum
    if parsed < 1:
        return 1
    if parsed > maximum:
        return maximum
    return parsed


def clamp_skip(skip: Any, maximum: int = MAX_LIST_DEPTH) -> int:
    """Return ``skip`` clamped to ``[0, maximum]`` (P5, pagination depth).

    Deep OFFSET scans are slow: cap the depth defensively at the repository
    so a client that bypasses the API-level validation (or passes a bogus
    value) never forces a huge offset query.
    """
    try:
        parsed = int(skip)
    except (TypeError, ValueError):
        return 0
    if parsed < 0:
        return 0
    if parsed > maximum:
        return maximum
    return parsed