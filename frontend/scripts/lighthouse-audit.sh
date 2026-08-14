#!/bin/bash
set -e
echo "🌐 Lighthouse Audit"
npm run build
npx serve out &
PID=$!
sleep 3
npx lighthouse http://localhost:3000 \
  --output=json \
  --output=html \
  --output-path=./lighthouse-report \
  --chrome-flags="--headless --no-sandbox" \
  --preset=mobile \
  --only-categories=performance,accessibility,best-practices || true
kill $PID 2>/dev/null || true
echo "✅ Report: ./lighthouse-report.html"