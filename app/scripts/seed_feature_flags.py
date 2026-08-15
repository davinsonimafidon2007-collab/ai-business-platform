"""Seed default feature flags — TASK-012.

Ejecutar una vez tras la migración:
    uv run python -m app.scripts.seed_feature_flags

Es idempotente: `FeatureFlagService.set_flag` crea o actualiza sin duplicar.
"""

from __future__ import annotations

import asyncio

from app.services.feature_flag_service import FeatureFlagService

DEFAULT_FLAGS = [
    ("enable_mobile_de", False, "Activar provider mobile.de (requiere proxy)"),
    ("enable_autoscout24_es", True, "Activar provider AutoScout24 ES"),
    ("enable_vision_analysis", False, "Activar análisis de visión con Gemini/OpenAI"),
    ("enable_push_notifications", False, "Activar notificaciones push móviles"),
    ("enable_opportunity_alerts", True, "Activar alertas por email de oportunidades"),
]


async def main() -> None:
    for key, value, desc in DEFAULT_FLAGS:
        flag = await FeatureFlagService.set_flag(key, value, desc)
        print(f"  OK: {flag.key} = {flag.value}")


if __name__ == "__main__":
    asyncio.run(main())