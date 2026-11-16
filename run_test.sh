#!/bin/bash
set -e

# Performance Test Runner with Project Selection
# Usage: ./run_test.sh [project-config.json] [duration-seconds]

# Configuration
DEFAULT_DURATION=60

# Function to list available projects
list_projects() {
    echo "📁 Available Projects:"
    echo "======================================"
    local i=1
    for config in projects/*.json; do
        if [ -f "$config" ]; then
            SERVICE_NAME=$(jq -r '.service_name' "$config" 2>/dev/null || echo "unknown")
            echo "  $i. $(basename "$config") - $SERVICE_NAME"
            ((i++))
        fi
    done
    echo ""
}

# If no arguments, list projects and prompt
if [ $# -eq 0 ]; then
    list_projects
    echo "Usage:"
    echo "  ./run_test.sh <config-file> [duration-seconds]"
    echo ""
    echo "Examples:"
    echo "  ./run_test.sh bcas-add-in-config.json"
    echo "  ./run_test.sh bcas-add-in-config.json 300"
    echo ""
    exit 0
fi

# Parse arguments
CONFIG_NAME="$1"
DURATION="${2:-$DEFAULT_DURATION}"

# Add projects/ prefix if not present
if [[ "$CONFIG_NAME" != projects/* ]] && [[ "$CONFIG_NAME" != /* ]]; then
    CONFIG_FILE="projects/$CONFIG_NAME"
else
    CONFIG_FILE="$CONFIG_NAME"
fi

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Configuration file not found: $CONFIG_FILE"
    echo ""
    list_projects
    exit 1
fi

# Extract service details from config
SERVICE_NAME=$(jq -r '.service_name' "$CONFIG_FILE")
BASE_URL=$(jq -r '.base_url' "$CONFIG_FILE")
NAMESPACE=$(echo "$SERVICE_NAME" | tr '_' '-')

echo "🚀 Performance Test with K8s Metrics"
echo "=================================================================="
echo "Project:      $SERVICE_NAME"
echo "Config:       $CONFIG_FILE"
echo "Base URL:     $BASE_URL"
echo "Namespace:    $NAMESPACE"
echo "Duration:     ${DURATION}s ($((DURATION/60))m $((DURATION%60))s)"
echo "=================================================================="

echo ""
echo "1️⃣  Pre-flight checks..."
if ! ./preflight.sh "$CONFIG_FILE"; then
    echo ""
    echo "❌ Pre-flight failed. Fix the issues above before running the test."
    exit 1
fi

# Generate test files
echo ""
echo "2️⃣  Generating test files..."
RUN_DIR=$(python -c "
import json
from jinja2 import Template
from pathlib import Path
from datetime import datetime, timezone

with open('$CONFIG_FILE') as f:
    config = json.load(f)

timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
run_dir = Path('runs') / timestamp
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / 'results').mkdir(exist_ok=True)

with open('templates/rest-api-jwt.py.j2') as f:
    template = Template(f.read())

endpoints_data = []
for i, ep in enumerate(config['endpoints']):
    ep_data = {
        'name': f\"endpoint_{i}\",
        'method': ep['method'],
        'path': ep['path'],
        'weight': ep['weight'],
        'requires_auth': ep.get('requires_auth', False),
        'requires_graph_token': ep.get('requires_graph_token', False)
    }
    if 'path_params' in ep:
        for param, value in ep['path_params'].items():
            ep_data['path'] = ep_data['path'].replace(f'{{{param}}}', value)
    if 'payload' in ep:
        ep_data['payload'] = json.dumps(ep['payload'])
    endpoints_data.append(ep_data)

locustfile = template.render(
    base_url=config['base_url'],
    jwt_token=config['credentials']['jwt_token'],
    graph_token=config['credentials'].get('graph_token', ''),
    endpoints=endpoints_data
)

with open(run_dir / 'locustfile.py', 'w') as f:
    f.write(locustfile)

with open(run_dir / 'config.json', 'w') as f:
    json.dump(config, f, indent=2)

print(run_dir)
")

echo "✅ Run directory: $RUN_DIR"

# Start K8s metrics collection (multi-service)
METRICS_FILE="$RUN_DIR/k8s_metrics.csv"

echo ""
echo "3️⃣  Starting K8s metrics collection (bcas-add-in + web-core-api)..."

# Run multi-service monitor in background
./monitor_multi_service.sh "$DURATION" "$METRICS_FILE" > "$RUN_DIR/k8s_monitor.log" 2>&1 &
METRICS_PID=$!
echo "✅ Metrics collection started (PID: $METRICS_PID)"
echo "   Monitoring: bcas-add-in, web-core-api"

# Run load test
echo ""
echo "4️⃣  Running load test..."
echo "=================================================================="
cd "$RUN_DIR"
locust -f locustfile.py \
  --host "$(jq -r '.base_url' config.json)" \
  --users "$(jq -r '.load_profile.users' config.json)" \
  --spawn-rate "$(jq -r '.load_profile.spawn_rate' config.json)" \
  --run-time "${DURATION}s" \
  --headless \
  --csv results/stats \
  --html results/report.html 2>&1 | tail -30

cd - > /dev/null
echo "=================================================================="

# Wait for metrics collection
echo ""
echo "5️⃣  Waiting for metrics collection..."
wait $METRICS_PID
echo "✅ Metrics collected"

# Analyze metrics (multi-service summary)
echo ""
echo "6️⃣  K8s Metrics Summary:"
for service in "bcas-add-in" "web-core-api"; do
    echo ""
    echo "   Service: $service"
    awk -F',' -v svc="$service" '
    $2 == svc && NR > 1 {
        cpu_sum += $7;
        mem_sum += $8;
        cpu_max = ($7 > cpu_max) ? $7 : cpu_max;
        mem_max = ($8 > mem_max) ? $8 : mem_max;
        count++
    }
    END {
        if (count > 0) {
            printf "     Average CPU:  %.1f%%\n", cpu_sum/count
            printf "     Peak CPU:     %.1f%%\n", cpu_max
            printf "     Average Mem:  %.1f%%\n", mem_sum/count
            printf "     Peak Mem:     %.1f%%\n", mem_max
        }
    }' "$METRICS_FILE"
done

# Generate reports
echo ""
echo "7️⃣  Generating reports..."
python plot_k8s_metrics.py "$METRICS_FILE" "$RUN_DIR/k8s_metrics_chart.html" 2>&1 | grep -v "^$"
python generate_enterprise_report.py "$RUN_DIR" 2>&1 | grep -E "✓|✅|🚦|🏭"

echo ""
echo "=================================================================="
echo "✅ Complete!"
echo "=================================================================="
echo ""
echo "📊 Reports:"
echo "   Performance: $RUN_DIR/PERFORMANCE_REPORT.html (includes K8s metrics)"
echo "   Locust:      $RUN_DIR/results/report.html"
echo ""
echo "🌐 Open main report:"
echo "   open $RUN_DIR/PERFORMANCE_REPORT.html"
echo ""
