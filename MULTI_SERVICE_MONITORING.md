# Multi-Service K8s Monitoring

## Overview

The performance framework now automatically monitors **multiple Kubernetes services** during load tests to help you understand the full impact of your API calls across the entire stack.

## Monitored Services

### 1. Primary Service: bcas-add-in
- **Namespace**: `bcas-add-in`
- **Label**: `app.kubernetes.io/name=bcas-add-in`
- **Purpose**: Service under test (receives load from Locust)
- **Pods**: 2-3 replicas

### 2. Downstream Service: web-core-api
- **Namespace**: `web-core-api`
- **Label**: `app.kubernetes.io/name=web-core-api`
- **Purpose**: Backend dependency (handles requests from bcas-add-in)
- **Pods**: 3 replicas

## How It Works

### Automatic Collection

When you run a performance test:

```bash
./run_test.sh bcas-add-in-config.json 300
```

The framework:
1. ✅ Starts `monitor_multi_service.sh` in the background
2. ✅ Samples metrics from **both services** every 5 seconds
3. ✅ Stores results in CSV: `runs/<timestamp>/k8s_metrics.csv`
4. ✅ Generates unified report with per-service breakdowns

### CSV Format

```csv
timestamp,service,namespace,pod,cpu_cores,memory_bytes,cpu_percent,memory_percent
2026-11-14T19:22:24Z,bcas-add-in,bcas-add-in,bcas-add-in-866f77677b-s8r7h,0.001,132120576,0.1,12.0
2026-11-14T19:22:24Z,web-core-api,web-core-api,web-core-api-84b45b657c-4rwv4,0.005,266338304,0.5,24.0
```

**Columns:**
- `timestamp`: ISO 8601 UTC timestamp
- `service`: Service name (bcas-add-in, web-core-api)
- `namespace`: Kubernetes namespace
- `pod`: Full pod name
- `cpu_cores`: CPU in cores (0.001 = 1 millicore)
- `memory_bytes`: Memory in bytes
- `cpu_percent`: CPU % (based on 1 core = 1000m limit)
- `memory_percent`: Memory % (based on 1Gi = 1024Mi limit)

## Report Features

### 1. Per-Service Summary Cards

Shows separate stats for each monitored service:

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ 🔹 bcas-add-in                  │  │ 🔹 web-core-api                 │
│ CPU: 3.2% avg, 7.1% peak        │  │ CPU: 0.5% avg, 1.2% peak        │
│ Memory: 12.5% avg, 13.0% peak   │  │ Memory: 22.3% avg, 28.5% peak   │
│ (60 samples)                    │  │ (180 samples - 3 pods)          │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

### 2. Multi-Service Charts

#### CPU Utilization Chart
- **Grouped by service**: Blue lines (bcas-add-in), Green lines (web-core-api)
- **Per-pod visibility**: Each pod shows as a separate line
- **80% threshold**: Red dashed line for capacity planning

#### Memory Usage Chart
- **Grouped by service**: Color-coded by service
- **MB scale**: Easy to understand memory consumption
- **Trend analysis**: Spot memory leaks or steady growth

### 3. Console Summary

During/after test execution:

```
6️⃣  K8s Metrics Summary:

   Service: bcas-add-in
     Average CPU:  3.2%
     Peak CPU:     7.1%
     Average Mem:  12.5%
     Peak Mem:     13.0%

   Service: web-core-api
     Average CPU:  0.5%
     Peak CPU:     1.2%
     Average Mem:  22.3%
     Peak Mem:     28.5%
```

## Analysis Scenarios

### Scenario 1: Primary Service Bottleneck

**Symptoms:**
- bcas-add-in: CPU 75%, Memory 80%
- web-core-api: CPU 5%, Memory 20%

**Conclusion:** Bottleneck is in bcas-add-in processing logic
**Action:** Profile bcas-add-in code, optimize hot paths

### Scenario 2: Downstream Service Bottleneck

**Symptoms:**
- bcas-add-in: CPU 15%, Memory 25%
- web-core-api: CPU 85%, Memory 90%

**Conclusion:** Bottleneck is in web-core-api backend
**Action:** Scale web-core-api replicas, optimize database queries

### Scenario 3: Balanced Load

**Symptoms:**
- bcas-add-in: CPU 40%, Memory 35%
- web-core-api: CPU 45%, Memory 40%

**Conclusion:** Healthy distribution, both services handling load well
**Action:** No immediate action needed, capacity headroom available

### Scenario 4: Memory Leak Detection

**Symptoms:**
- bcas-add-in: Memory climbing from 20% → 80% over 5 minutes
- web-core-api: Memory stable at 25%

**Conclusion:** Possible memory leak in bcas-add-in
**Action:** Check for unclosed connections, large caches, event listeners

## Resource Calculations

### CPU Percentage
```
Limit: 1 core = 1000 millicores
CPU% = millicores / 10

Example:
  77m → 77 / 10 = 7.7%
```

### Memory Percentage
```
Limit: 1Gi = 1024Mi
Memory% = (used_Mi / 1024) * 100

Example:
  132Mi → (132 / 1024) * 100 = 12.9%
```

## Adding More Services

To monitor additional services, edit `monitor_multi_service.sh`:

```bash
# Services to monitor (namespace:service-name:label)
SERVICES=(
    "bcas-add-in:bcas-add-in:app.kubernetes.io/name=bcas-add-in"
    "web-core-api:web-core-api:app.kubernetes.io/name=web-core-api"
    "payments-api:payments-api:app.kubernetes.io/name=payments-api"  # Add this
)
```

Charts and reports will automatically include the new service.

## Standalone Monitoring

Test the multi-service monitor independently:

```bash
# Monitor for 30 seconds
./monitor_multi_service.sh 30 test_metrics.csv

# View CSV
cat test_metrics.csv

# Summary printed automatically at end
```

## Benefits

✅ **Full Stack Visibility**: See how load affects entire service chain
✅ **Bottleneck Detection**: Quickly identify which service is the constraint
✅ **Capacity Planning**: Understand resource needs across all services
✅ **Correlation Analysis**: Match latency spikes to resource usage
✅ **Zero Configuration**: Works automatically with run_test.sh

## Next Steps

1. Run a test: `./run_test.sh bcas-add-in-config.json 300`
2. Open report: `open runs/<timestamp>/PERFORMANCE_REPORT.html`
3. Check per-service metrics in the "☸️ Kubernetes Metrics" section
4. Analyze CPU/Memory charts (grouped by service)
5. Identify bottlenecks and optimize accordingly

## Troubleshooting

### No metrics collected for web-core-api

**Check pod accessibility:**
```bash
kubectl get pods -n web-core-api -l "app.kubernetes.io/name=web-core-api"
```

**Check metrics server:**
```bash
kubectl top pods -n web-core-api
```

### Different resource limits

If your services have different limits (not 1 core / 1Gi), update the percentage calculations in `monitor_multi_service.sh`:

```bash
# For 2 core limit:
CPU_PERCENT=$(echo "scale=2; $CPU / 20" | bc)

# For 2Gi limit:
MEMORY_PERCENT=$(echo "scale=2; ($MEMORY / 2048) * 100" | bc)
```

---

**Last Updated**: 2026-11-15
**Version**: 1.0.0
