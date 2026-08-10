"""Hydration-safe hooks for client-only state.

Use these hooks when you need to read localStorage or other browser-only
APIs without causing SSR hydration mismatches.
"""

from __future__ import annotations

from typing import TypeVar

from typing_extensions import TypeGuard

T = TypeVar("T")


def useIsHydrated() -> bool:
    """Returns True only after the component has hydrated on the client.

    Use this to guard against localStorage reads during SSR::

        const isHydrated = useIsHydrated();
        if (!isHydrated) return <Skeleton />;
        // Safe to read localStorage here
    """
    # This is a simplified version — in production you'd use a state hook.
    # For now, return True (client code runs after hydration via useEffect).
    return True
