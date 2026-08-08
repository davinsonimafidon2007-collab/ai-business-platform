"""Correlation ID utilities for distributed tracing.

Provides a context variable for propagating correlation IDs across
asynchronous boundaries within the same request lifecycle.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID (UUID v4).

    Returns:
        A new UUID4 string to use as correlation ID.
    """
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        The current correlation ID, or None if not set.
    """
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in the current context.

    Args:
        correlation_id: The correlation ID to set.
    """
    _correlation_id_ctx.set(correlation_id)


def reset_correlation_id() -> None:
    """Reset the correlation ID in the current context to None."""
    _correlation_id_ctx.set(None)

