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