#!/bin/bash
set -e

# Multi-Service K8s Metrics Monitor
# Collects CPU and Memory from multiple services during performance tests
# Usage: ./monitor_multi_service.sh <duration> <output-file>

DURATION=${1:-60}
OUTPUT_FILE=${2:-k8s_metrics_multi.csv}

# Services to monitor (namespace:service-name:label)
SERVICES=(
    "bcas-add-in:bcas-add-in:app.kubernetes.io/name=bcas-add-in"
    "web-core-api:web-core-api:app.kubernetes.io/name=web-core-api"
)

echo "📊 Multi-Service K8s Metrics Monitor"
echo "======================================================================"
echo "Duration:       ${DURATION}s"
echo "Output:         $OUTPUT_FILE"
echo "Services:       ${#SERVICES[@]}"
for svc in "${SERVICES[@]}"; do
    IFS=':' read -r ns name label <<< "$svc"
    echo "  - $name (namespace: $ns)"
done
echo "======================================================================"
echo ""

# Initialize CSV
echo "timestamp,service,namespace,pod,cpu_cores,memory_bytes,cpu_percent,memory_percent" > "$OUTPUT_FILE"

# Calculate end time
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))
SAMPLE_INTERVAL=5

echo "⏱️  Starting collection (sampling every ${SAMPLE_INTERVAL}s)..."
echo ""

# Collection loop
while [ $(date +%s) -lt $END_TIME ]; do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Collect from each service
    for svc in "${SERVICES[@]}"; do
        IFS=':' read -r namespace service_name label <<< "$svc"

        kubectl top pods -n "$namespace" -l "$label" --no-headers 2>/dev/null | while read -r line; do
            POD=$(echo "$line" | awk '{print $1}')
            CPU=$(echo "$line" | awk '{print $2}' | sed 's/m$//')
            MEMORY=$(echo "$line" | awk '{print $3}' | sed 's/Mi$//')

            # Convert to standard units
            CPU_CORES=$(echo "scale=3; $CPU / 1000" | bc)
            MEMORY_BYTES=$(echo "$MEMORY * 1024 * 1024" | bc)

            # Calculate percentages (assuming 1 core, 1Gi limits)
            CPU_PERCENT=$(echo "scale=2; $CPU / 10" | bc)
            MEMORY_PERCENT=$(echo "scale=2; ($MEMORY / 1024) * 100" | bc)

            # Append to CSV
            echo "$TIMESTAMP,$service_name,$namespace,$POD,$CPU_CORES,$MEMORY_BYTES,$CPU_PERCENT,$MEMORY_PERCENT" >> "$OUTPUT_FILE"

            # Print to console
            printf "[%s] %-15s | %s | CPU: %.3f cores (%5.1f%%) | Memory: %4sMi (%5.1f%%)\n" \
                "$TIMESTAMP" "$service_name" "$POD" "$CPU_CORES" "$CPU_PERCENT" "$MEMORY" "$MEMORY_PERCENT"
        done
    done

    sleep $SAMPLE_INTERVAL
done

echo ""
echo "======================================================================"
echo "✅ Collection complete!"
echo "📁 Saved to: $OUTPUT_FILE"
echo ""
echo "📊 Summary Statistics:"
echo ""

# Generate summary per service
for svc in "${SERVICES[@]}"; do
    IFS=':' read -r namespace service_name label <<< "$svc"

    echo "Service: $service_name"
    awk -F',' -v service="$service_name" '
    $2 == service && NR > 1 {
        cpu_sum += $7;
        mem_sum += $8;
        cpu_max = ($7 > cpu_max) ? $7 : cpu_max;
        mem_max = ($8 > mem_max) ? $8 : mem_max;
        count++
    }
    END {
        if (count > 0) {
            printf "  Average CPU:  %.1f%%\n", cpu_sum/count
            printf "  Peak CPU:     %.1f%%\n", cpu_max
            printf "  Average Mem:  %.1f%%\n", mem_sum/count
            printf "  Peak Mem:     %.1f%%\n", mem_max
            printf "  Samples:      %d\n", count
        }
    }' "$OUTPUT_FILE"
    echo ""
done

echo "======================================================================"
