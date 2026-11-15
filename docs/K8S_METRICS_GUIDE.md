# Kubernetes Metrics Collection Guide
**Measure CPU & Memory Utilization During Performance Tests**

---

## 📊 Overview

This guide shows you how to collect CPU and Memory metrics from your Kubernetes pods while running performance tests, then visualize the correlation between load and resource utilization.

---

## 🎯 Three Collection Methods

### Method 1: Real-Time kubectl Monitoring (Quick & Simple)

**Best for:** Quick checks, manual observation

```bash
# Watch metrics update every 2 seconds
watch -n 2 'kubectl top pods -n <namespace> -l app=<service-name>'

# Example for BCAS Add-in
watch -n 2 'kubectl top pods -n bcas-qa -l app=bcas-add-in'
```

**Output:**
```
NAME                          CPU(cores)   MEMORY(bytes)
bcas-add-in-7d9f8c6b4-abc12   145m         512Mi
bcas-add-in-7d9f8c6b4-def34   138m         498Mi
```

**Pros:** Instant, no setup  
**Cons:** Manual, no historical data

---

### Method 2: Automated Timeline Collection (Recommended)

**Best for:** Correlating metrics with load test results

#### Step 1: Run monitoring script in parallel with load test

```bash
# Terminal 1: Start metrics collection (services are configured inside the script)
./monitor_multi_service.sh <duration> <output-file>

# Example: Monitor for 5 minutes (300s)
./monitor_multi_service.sh 300 bcas_metrics.csv
```

#### Step 2: Run your load test (in separate terminal)

```bash
# Terminal 2: Run performance test
/perf-execute for 5 min
```

#### Step 3: Visualize collected metrics

```bash
python plot_k8s_metrics.py bcas_metrics.csv bcas_k8s_chart.html
open bcas_k8s_chart.html
```

**What you get:**
- CSV timeline of CPU/Memory every 5 seconds
- Interactive charts with CPU and Memory %
- Statistics (avg, max, min)
- Correlation with load test timing

---

### Method 3: Prometheus Queries (Advanced)

**Best for:** Historical analysis, long-term trends

#### A. Query via API

```bash
# CPU usage (millicores) over last 5 minutes
curl "https://prometheus.company.com/api/v1/query_range" \
  --data-urlencode 'query=rate(container_cpu_usage_seconds_total{namespace="bcas-qa",pod=~"bcas-add-in.*"}[1m])*1000' \
  --data-urlencode 'start=2026-11-14T17:48:00Z' \
  --data-urlencode 'end=2026-11-14T17:53:00Z' \
  --data-urlencode 'step=15s'

# Memory usage (bytes)
curl "https://prometheus.company.com/api/v1/query_range" \
  --data-urlencode 'query=container_memory_working_set_bytes{namespace="bcas-qa",pod=~"bcas-add-in.*"}' \
  --data-urlencode 'start=2026-11-14T17:48:00Z' \
  --data-urlencode 'end=2026-11-14T17:53:00Z' \
  --data-urlencode 'step=15s'
```

#### B. Use Python script

```bash
python fetch_k8s_metrics.py \
  --namespace bcas-qa \
  --service bcas-add-in \
  --prometheus https://prometheus.company.com \
  --output k8s_report.md
```

---

## 🚀 Complete Workflow Example

### Full end-to-end performance test with K8s metrics

```bash
# 1. Start K8s metrics collection (5 min = 300s)
./monitor_multi_service.sh 300 metrics.csv &
MONITOR_PID=$!

# 2. Wait 5 seconds for monitoring to initialize
sleep 5

# 3. Run performance test (5 minutes)
/perf-execute for 5 min

# 4. Wait for monitoring to complete
wait $MONITOR_PID

# 5. Generate visualizations
python plot_k8s_metrics.py metrics.csv k8s_chart.html

# 6. Generate performance report
/perf-report

# 7. Open both reports
open runs/*/PERFORMANCE_REPORT.html
open k8s_chart.html
```

**Result:** You'll have:
- Load test metrics (RPS, latency, errors)
- K8s resource utilization (CPU, Memory)
- Timeline correlation between load and resources

---

## 📈 Understanding the Metrics

### CPU Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **CPU (cores)** | Number of CPU cores used | < limit |
| **CPU %** | Percentage of limit used | < 80% |
| **CPU millicores (m)** | 1000m = 1 core | - |

**Example:**
```
CPU: 450m = 0.45 cores = 45% of 1-core limit
```

### Memory Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Memory (bytes)** | RAM usage | < limit |
| **Memory %** | Percentage of limit used | < 80% |
| **Mi / Gi** | Mebibytes / Gibibytes | - |

**Example:**
```
Memory: 512Mi = 536,870,912 bytes = 50% of 1Gi limit
```

---

## 🎯 Resource Utilization Analysis

### Healthy Resource Usage

```
✅ Good:
- CPU: 40-60% average, spikes to 70-80% under load
- Memory: 50-70% stable, gradual growth
- No OOM (Out of Memory) kills
- Headroom for traffic spikes
```

### Warning Signs

```
⚠️  Warning:
- CPU: Sustained 80%+ (add CPU limits or scale up)
- Memory: 90%+ (risk of OOM kills)
- CPU: 10-20% (over-provisioned, waste of resources)
- Memory spikes: Potential memory leaks
```

### Critical Issues

```
🔴 Critical:
- CPU throttling (requests delayed)
- OOM kills (pod restarts)
- CPU: 100% sustained (bottleneck)
- Memory: Linear growth (memory leak)
```

---

## 🔧 Prerequisites

### 1. kubectl Access

```bash
# Verify kubectl access
kubectl get pods -n <namespace>

# Verify metrics-server is running
kubectl top nodes
```

If `kubectl top` fails:
```bash
# Check if metrics-server is installed
kubectl get deployment metrics-server -n kube-system

# If not installed, ask your DevOps team to install it
```

### 2. Python Dependencies

```bash
# Install required packages
pip install pandas plotly requests
```

### 3. K8s Permissions

You need these permissions in your namespace:
- `pods/get` (list pods)
- `pods/log` (optional, for logs)

---

## 📊 Correlation Analysis

### Compare Load vs Resources

#### Scenario 1: Linear Scaling (Good)
```
Load:      100 RPS → 200 RPS → 300 RPS
CPU:       40%     → 60%     → 80%
Memory:    512Mi   → 512Mi   → 512Mi

✅ CPU scales linearly with load
✅ Memory stable (no leaks)
```

#### Scenario 2: CPU Bottleneck
```
Load:      100 RPS → 200 RPS → 300 RPS
CPU:       70%     → 95%     → 100% (throttled)
Latency:   200ms   → 450ms   → 1200ms

🔴 CPU saturated at 200 RPS
🔴 Latency increases exponentially
Action: Add CPU limits or scale pods
```

#### Scenario 3: Memory Leak
```
Time:      0min → 2min → 4min → 6min
Memory:    200Mi → 400Mi → 600Mi → 800Mi
Load:      Constant 150 RPS

🔴 Memory growing linearly under constant load
Action: Investigate memory leak in application
```

---

## 🎨 Visualization Tips

### Overlay Metrics

Combine Locust + K8s metrics in single view:

1. **Export Locust timeline:**
   ```bash
   # From stats_stats_history.csv
   timestamp, RPS, p95_latency
   ```

2. **Export K8s timeline:**
   ```bash
   # From k8s_metrics_timeline.csv
   timestamp, cpu_percent, memory_percent
   ```

3. **Merge and plot:**
   ```python
   import pandas as pd
   import plotly.graph_objects as go
   from plotly.subplots import make_subplots

   # Load both CSVs
   locust = pd.read_csv('stats_stats_history.csv')
   k8s = pd.read_csv('k8s_metrics_timeline.csv')

   # Merge on timestamp
   merged = pd.merge(locust, k8s, on='timestamp', how='outer')

   # Plot combined chart
   fig = make_subplots(
       rows=3, cols=1,
       subplot_titles=('Requests/sec', 'Response Time (p95)', 'CPU & Memory %')
   )

   # RPS
   fig.add_trace(go.Scatter(x=merged['timestamp'], y=merged['Requests/s'], name='RPS'), row=1, col=1)

   # Latency
   fig.add_trace(go.Scatter(x=merged['timestamp'], y=merged['95%'], name='p95'), row=2, col=1)

   # CPU and Memory
   fig.add_trace(go.Scatter(x=merged['timestamp'], y=merged['cpu_percent'], name='CPU %'), row=3, col=1)
   fig.add_trace(go.Scatter(x=merged['timestamp'], y=merged['memory_percent'], name='Memory %'), row=3, col=1)

   fig.write_html('combined_metrics.html')
   ```

---

## 📁 File Structure

After running metrics collection:

```
perf-framework/
├── runs/
│   └── 2026-11-14T17-48-21Z/
│       ├── PERFORMANCE_REPORT.html    # Locust metrics
│       ├── k8s_metrics.csv            # K8s timeline
│       ├── k8s_metrics_chart.html     # K8s visualization
│       └── combined_metrics.html      # Combined view
├── monitor_multi_service.sh           # Monitoring script
├── fetch_k8s_metrics.py              # K8s collector
├── plot_k8s_metrics.py               # Visualization
└── K8S_METRICS_GUIDE.md              # This file
```

---

## 🎯 Common Use Cases

### 1. Capacity Planning

**Question:** Can we handle 2x traffic?

```bash
# Current: 100 RPS at 50% CPU
# Test: 200 RPS

./monitor_multi_service.sh 300 capacity_test.csv &
/perf-execute --users 20 --duration 300  # 2x users

# Check if CPU stays under 80%
python plot_k8s_metrics.py capacity_test.csv
```

### 2. Resource Optimization

**Question:** Are we over-provisioned?

```bash
# Check average CPU/Memory usage
./monitor_multi_service.sh 600 optimization.csv &

# If avg CPU < 30% and avg Memory < 40%:
# → Consider reducing resource limits
```

### 3. Bottleneck Identification

**Question:** Is backend or client the bottleneck?

```bash
# Compare client-side latency vs server-side CPU
# If CPU < 50% but latency high:
#   → Bottleneck is NOT compute (maybe DB, cache, network)
# If CPU > 90% and latency high:
#   → CPU bottleneck (need more resources or optimization)
```

---

## 🚨 Troubleshooting

### kubectl top not working

```bash
# Check metrics-server
kubectl get deployment metrics-server -n kube-system

# If not found, install it (requires admin)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### No metrics-server access

Use Prometheus instead:

```bash
python fetch_k8s_metrics.py \
  --namespace bcas-qa \
  --service bcas-add-in \
  --prometheus https://prometheus.company.com
```

### Monitoring script permission denied

```bash
chmod +x monitor_multi_service.sh
```

---

## 📚 Additional Resources

### Kubernetes Resource Management
- [K8s Resource Requests and Limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [K8s Metrics Server](https://github.com/kubernetes-sigs/metrics-server)

### Prometheus Queries
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Container Metrics](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)

---

**Last Updated:** 2026-11-14  
**Framework Version:** perf-framework v1.0
