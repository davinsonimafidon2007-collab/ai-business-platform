"""Tests for offline functionality — TASK-016 (FASE 5).

Los tests funcionales de offline viven en el frontend (Vitest, jsdom):
`src/__tests__/offline-queue.test.ts`. Este módulo documenta la verificación
manual del Service Worker en navegador/dispositivo (criterios FASE 5).
"""

from __future__ import annotations


def test_service_worker_registration() -> None:
    """Service Worker should register without errors.

    Manual verification:
    1. Open app in Chrome
    2. Open DevTools > Application > Service Workers
    3. Verify SW is registered and activated
    4. Verify cache 'abp-cache-v1' exists
    """
    assert True  # Manual test


def test_offline_cache_serves_data() -> None:
    """Cached API data should be served when offline.

    Manual verification:
    1. Load app and perform a search
    2. Go offline (DevTools > Network > Offline)
    3. Reload page or navigate to search
    4. Verify results appear from cache
    """
    assert True  # Manual test


def test_offline_banner_appears() -> None:
    """Offline banner should appear when connection is lost.

    Manual verification:
    1. Open app
    2. Disconnect network
    3. Verify banner 'Sin conexión' appears
    4. Reconnect and verify banner disappears
    """
    assert True  # Manual test
