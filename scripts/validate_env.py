#!/usr/bin/env python3
"""Validar que todas las variables de entorno requeridas están definidas."""
import os
import sys

REQUIRED_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET_KEY",
    "CORS_ORIGINS",
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    sys.exit(1)
print("✅ All required environment variables are set.")
