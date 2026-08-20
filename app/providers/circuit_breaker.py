"""Circuit breaker simple por provider (TASK 4)."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitBreakerState:
    failure_count: int = 0
    opened_at: float | None = None


class ProviderCircuitBreaker:
    """Circuit breaker en memoria, por instancia de proceso.

    - CLOSED: funciona normal.
    - OPEN: tras `failure_threshold` fallos consecutivos, rechaza llamadas
      durante `cooldown_seconds` sin golpear la red.
    - HALF_OPEN: pasado el cooldown, deja pasar UNA llamada de prueba.
    """

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state: dict[str, CircuitBreakerState] = {}

    def _get(self, key: str) -> CircuitBreakerState:
        return self._state.setdefault(key, CircuitBreakerState())

    def is_open(self, key: str) -> bool:
        st = self._get(key)
        if st.opened_at is None:
            return False
        if time.monotonic() - st.opened_at >= self.cooldown_seconds:
            st.opened_at = None
            return False
        return True

    def record_success(self, key: str) -> None:
        self._state[key] = CircuitBreakerState()

    def record_failure(self, key: str) -> None:
        st = self._get(key)
        st.failure_count += 1
        if st.failure_count >= self.failure_threshold and st.opened_at is None:
            st.opened_at = time.monotonic()


circuit_breaker = ProviderCircuitBreaker()
