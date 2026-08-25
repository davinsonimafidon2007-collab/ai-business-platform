from __future__ import annotations

from app.providers.circuit_breaker import ProviderCircuitBreaker


def test_open_after_consecutive_failures() -> None:
    breaker = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=5.0)
    provider = "mobile_de"

    assert breaker.is_open(provider) is False

    breaker.record_failure(provider)
    assert breaker.is_open(provider) is False

    breaker.record_failure(provider)
    assert breaker.is_open(provider) is False

    breaker.record_failure(provider)
    assert breaker.is_open(provider) is True


def test_rejects_call_while_open() -> None:
    breaker = ProviderCircuitBreaker(failure_threshold=2, cooldown_seconds=5.0)
    provider = "mobile_de"

    breaker.record_failure(provider)
    breaker.record_failure(provider)

    assert breaker.is_open(provider) is True
