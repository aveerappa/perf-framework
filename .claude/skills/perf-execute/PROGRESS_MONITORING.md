# Real-Time Progress Monitoring

## Approach for Showing Test Progress

When running tests in background, use the `Monitor` tool to stream live updates to the user.

### Method 1: Monitor Background Test Output (Recommended)

```bash
# Start test in background
./run_test.sh config.json 300 > /tmp/test_output.log 2>&1 &
TEST_PID=$!

# Monitor the output file for updates
tail -f /tmp/test_output.log | grep -E "RPS|p95|Users|Error|✓|✅|Complete"
```

**Using Monitor tool:**

```python
Monitor({
    'command': 'tail -f /tmp/test_output.log | grep --line-buffered -E "RPS|p95|Users|Error|✓|✅|Complete|Requests/s"',
    'description': 'Performance test progress',
    'timeout_ms': 660000  # Slightly longer than test duration
})
```

### Method 2: Progress Script with Monitor

```python
# Start test
task_id = start_background_test()

# Monitor with custom script
Monitor({
    'command': f'./show_test_progress.sh {run_dir} {duration}',
    'description': 'Test progress bar and stats',
    'timeout_ms': duration * 1000 + 60000
})
```

### Method 3: Parse Locust Stats in Real-Time

Monitor the Locust stats history CSV as it's being written:

```python
Monitor({
    'command': f'''
        while [ ! -f "{run_dir}/results/stats_stats_history.csv" ]; do sleep 1; done
        tail -f "{run_dir}/results/stats_stats_history.csv" | while read line; do
            if [ -n "$line" ]; then
                RPS=$(echo "$line" | awk -F',' '{{print $10}}')
                P95=$(echo "$line" | awk -F',' '{{print $8}}')
                echo "RPS: $RPS | p95: ${{P95}}ms"
            fi
        done
    ''',
    'description': 'Live Locust metrics',
    'timeout_ms': duration * 1000 + 60000
})
```

## Visual Progress Bar

For console progress bars, use a shell script:

```bash
#!/bin/bash
DURATION=$1
START=$(date +%s)
END=$((START + DURATION))

while [ $(date +%s) -lt $END ]; do
    ELAPSED=$(($(date +%s) - START))
    PCT=$((ELAPSED * 100 / DURATION))
    BARS=$((PCT / 2))

    printf "\r["
    printf "%${BARS}s" | tr ' ' '█'
    printf "%$((50-BARS))s" | tr ' ' '░'
    printf "] %3d%%" "$PCT"

    sleep 1
done
echo ""
```

## Example Integration in Skill

```python
# In perf-execute skill
def run_with_progress(config_file, duration):
    # Start test in background
    run_dir = start_test_background(config_file, duration)

    # Show progress to user
    Monitor({
        'command': f'''
            duration={duration}
            start=$(date +%s)
            end=$((start + duration))

            while [ $(date +%s) -lt $end ]; do
                elapsed=$(($(date +%s) - start))
                pct=$((elapsed * 100 / duration))
                bars=$((pct / 2))

                printf "\\r⏱️  ["
                printf "%${{bars}}s" | tr ' ' '█'
                printf "%$((50-bars))s" | tr ' ' '░'
                printf "] %3d%% | %ds/%ds" "$pct" "$elapsed" "$duration"

                # Show latest metrics if available
                if [ -f "{run_dir}/results/stats_stats_history.csv" ]; then
                    latest=$(tail -1 "{run_dir}/results/stats_stats_history.csv" 2>/dev/null)
                    rps=$(echo "$latest" | awk -F',' '{{print $10}}')
                    if [ -n "$rps" ]; then
                        printf " | RPS: %s" "$rps"
                    fi
                fi

                sleep 2
            done
            echo ""
            echo "✅ Test complete!"
        ''',
        'description': f'Performance test progress ({duration}s)',
        'timeout_ms': duration * 1000 + 120000
    })
```

## User Experience

**What the user sees:**

```
📊 Performance Test Progress Monitor
==================================================================
Duration: 300s | Run: 2026-11-14T19-26-14Z
==================================================================

⏱️  [████████████████░░░░░░░░░░░░░░░░░░░] 62% | 186s/300s | RPS: 38.7

📈 Latest Stats:
   RPS: 38.7 req/s
   p95: 3450ms
   Errors: 0.2%
```

## Benefits

✅ **Real-time visibility**: User sees progress immediately
✅ **No polling**: Monitor tool streams updates automatically
✅ **Live metrics**: Shows RPS, latency, errors as they happen
✅ **Visual feedback**: Progress bar shows time remaining
✅ **Early detection**: User sees errors/issues during test, not after

## When Test Completes

Monitor automatically stops when:
- Test duration reaches end
- Test process exits
- Monitor timeout reached

Then show final summary and report path.
