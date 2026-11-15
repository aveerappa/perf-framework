#!/bin/bash
# Emits one live-stats line every INTERVAL seconds while run_test.sh runs.
# Usage: monitor_progress.sh <output-log> <duration-seconds> [interval-seconds=60]

OUTPUT_LOG="$1"
DURATION="$2"
INTERVAL="${3:-60}"
START=$(date +%s)

run_dir() {
    grep -o 'Run directory: .*' "$OUTPUT_LOG" 2>/dev/null | tail -1 | sed 's/Run directory: //'
}

finished() {
    grep -q "Complete!" "$OUTPUT_LOG" 2>/dev/null
}

# Latest Aggregated row of Locust's stats history:
# 2=users 5=rps 6=fail/s 7=p50 12=p95 18=total requests 19=total failures
stats_line() {
    local hist="$1/results/stats_stats_history.csv"
    [ -f "$hist" ] || return 1
    grep ',Aggregated,' "$hist" | tail -1 | awk -F',' '
        NF >= 19 {
            flag = ""
            if ($6 > 0)    flag = flag " ⚠️ errors"
            if ($7 > 5000) flag = flag " ⚠️ p50>5s"
            printf "users=%s  rps=%.0f  fail/s=%.0f  p50=%sms  p95=%sms  total=%s req (%s failed)%s",
                   $2, $5, $6, $7, $12, $18, $19, flag
        }'
}

echo "📊 Performance test started — live update every ${INTERVAL}s (planned ${DURATION}s)"

while ! finished; do
    for ((i = 0; i < INTERVAL; i++)); do
        sleep 1
        finished && break 2
    done

    ELAPSED=$(( $(date +%s) - START ))
    if [ "$ELAPSED" -gt $((DURATION + 180)) ]; then
        echo "⚠️  ${ELAPSED}s elapsed and test has not completed — check $OUTPUT_LOG"
        exit 1
    fi

    RUN_DIR=$(run_dir)
    if [ -z "$RUN_DIR" ]; then
        echo "⏱️  ${ELAPSED}s/${DURATION}s  validating config / generating test files..."
        continue
    fi

    STATS=$(stats_line "$RUN_DIR")
    if [ -n "$STATS" ]; then
        echo "⏱️  ${ELAPSED}s/${DURATION}s  $STATS"
    else
        echo "⏱️  ${ELAPSED}s/${DURATION}s  locust starting, no stats yet"
    fi
done

ELAPSED=$(( $(date +%s) - START ))
RUN_DIR=$(run_dir)
echo "✅ Test complete in ${ELAPSED}s"
STATS=$(stats_line "$RUN_DIR")
[ -n "$STATS" ] && echo "   final: $STATS"
REPORT=$(grep -o 'runs/[^ ]*/PERFORMANCE_REPORT.html' "$OUTPUT_LOG" | tail -1)
[ -n "$REPORT" ] && echo "   open $REPORT"
