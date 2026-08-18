#!/bin/bash
# scripts/audit_dependencies.sh
# Audita dependencias de Python y Node.js en busca de vulnerabilidades

set -e

echo "🔍 Auditing Python dependencies..."
if command -v pip-audit &> /dev/null; then
    pip-audit --requirement requirements.txt || true
else
    echo "⚠️ pip-audit not installed. Install with: pip install pip-audit"
fi

if command -v safety &> /dev/null; then
    safety check -r requirements.txt || true
else
    echo "⚠️ safety not installed. Install with: pip install safety"
fi

echo "🔍 Auditing Node.js dependencies..."
if command -v npm &> /dev/null; then
    cd frontend
    npm audit --production || true
    cd ..
else
    echo "⚠️ npm not found"
fi

echo "✅ Audit completed."
