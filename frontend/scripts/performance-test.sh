#!/bin/bash
set -e
PACKAGE="com.aibusiness.platform"
RESULTS_DIR="performance-results"
mkdir -p "$RESULTS_DIR"

echo "📊 Performance Tests"
echo "===================="

# Cold Start
adb shell am force-stop "$PACKAGE" 2>/dev/null || true
sleep 2
START=$(date +%s%N)
adb shell am start -n "$PACKAGE/.MainActivity" > /dev/null
sleep 10
END=$(date +%s%N)
COLD=$(( (END - START) / 1000000 ))
echo "Cold Start: ${COLD}ms"
echo "cold_start_ms,$COLD" >> "$RESULTS_DIR/metrics.csv"

# Memory
MEM=$(adb shell dumpsys meminfo "$PACKAGE" 2>/dev/null | grep "TOTAL" | awk '{print $2}' || echo "N/A")
echo "Memory: ${MEM}KB"
echo "memory_kb,$MEM" >> "$RESULTS_DIR/metrics.csv"

# APK Size
APK="android/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK" ]; then
    SIZE=$(stat -c%s "$APK" 2>/dev/null || stat -f%z "$APK")
    SIZE_MB=$(echo "scale=2; $SIZE / 1024 / 1024" | bc)
    echo "APK Size: ${SIZE_MB}MB"
    echo "apk_size_mb,$SIZE_MB" >> "$RESULTS_DIR/metrics.csv"
fi

echo ""
echo "Results: $RESULTS_DIR/metrics.csv"
cat "$RESULTS_DIR/metrics.csv"