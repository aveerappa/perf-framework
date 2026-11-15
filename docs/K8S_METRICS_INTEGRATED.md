# K8s Metrics Integrated into Performance Reports

**Date:** 2026-11-14

## ✅ What Changed

CPU and Memory metrics from Kubernetes are now **automatically included** in every performance report when available.

## 📊 New Report Structure

### Single Unified Report
`PERFORMANCE_REPORT.html` now includes:

**1. Summary Cards (Top Section)**
- Total Requests
- Success Rate
- Error Rate
- P50/P95/P99 Latency
- **NEW: CPU Usage (Avg & Peak)** 🆕
- **NEW: Memory Usage (Avg & MB)** 🆕

**2. Performance Charts**
- Response Time Percentiles
- Requests Per Second
- Error Rate
- Request Distribution
- Endpoint Latency

**3. Kubernetes Metrics Section** 🆕
- **Resource Utilization Analysis Box**
  - CPU statistics with headroom calculation
  - Memory statistics
  - Automatic bottleneck detection (CPU vs I/O)
- **CPU Utilization Chart**
  - Per-pod CPU % over time
  - 80% threshold line
  - Interactive timeline
- **Memory Usage Chart**
  - Per-pod Memory MB over time
  - Stacked area visualization
  - Leak detection

**4. SLA Compliance Table**
- P50/P95/P99 thresholds
- Error rate threshold
- Pass/Fail status

**5. Failures Analysis**
- Error breakdown by endpoint
- Occurrence counts

## 🔄 Automatic Detection

The report generator (`generate_report.py`) now:
1. Checks if `k8s_metrics.csv` exists in the run directory
2. If found: Loads metrics and adds K8s section
3. If not found: Generates standard report (no K8s section)

**No manual intervention needed!**

## 🚀 How to Use

### Run Test with Metrics (Automatic)
```bash
./run_test_now.sh
```

This will:
1. Collect K8s metrics during test (every 5 seconds)
2. Run Locust load test
3. Generate **unified report** with both performance + K8s metrics
4. Open the single comprehensive report

### Generate Report After Test
```bash
# For latest run
python generate_report.py

# For specific run
python generate_report.py runs/2026-11-14T18-21-28Z/
```

If `k8s_metrics.csv` exists in the run directory, K8s metrics are automatically included.

## 📈 What You Get

### Example Output (Test with K8s Metrics)
```
📊 Performance Test Report Generator
============================================================
Run Directory: runs/2026-11-14T18-21-28Z
Loading test results...
✓ K8s metrics found, loading...
✓ Loaded 24 K8s metric samples
✓ Loaded 9 endpoint stats
✓ Loaded 60 history records

📊 Generating charts...
  1. Response time percentiles...
  2. Requests per second...
  3. Error rate...
  4. Request distribution...
  5. Response times by endpoint...
  6. K8s CPU utilization...          ← NEW
  7. K8s Memory usage...             ← NEW

✅ Report generated successfully!
```

### Example K8s Analysis in Report
```
📊 Resource Utilization Analysis

CPU Usage: 1.1% average, 2.0% peak (98% headroom available)
Memory Usage: 12.3% average, 12.3% peak (126 MB average)

Analysis: ✅ Low CPU with high latency suggests I/O bottleneck 
(external services, database, network)
```

## 🎯 Bottleneck Detection

The report automatically analyzes:

### High CPU Scenario
```
CPU: 75% average, 90% peak
Analysis: ⚠️ High CPU utilization indicates compute bottleneck
```
**Action:** Scale pods or optimize code

### Low CPU + High Latency
```
CPU: 1-2% average
P95 Latency: 1000ms
Analysis: ✅ Low CPU with high latency suggests I/O bottleneck
```
**Action:** Optimize external service calls (S3, Elasticsearch, etc.)

## 📁 File Changes

### Modified Files

**1. `generate_report.py`**
- Added K8s metrics detection (`k8s_metrics.csv`)
- Calculate K8s statistics (avg, max, min CPU/Memory)
- Generate CPU utilization chart (per-pod, with threshold)
- Generate Memory usage chart (per-pod, stacked)
- Add K8s metrics cards to summary
- Add Kubernetes Metrics section with analysis
- Automatic I/O vs CPU bottleneck detection

**2. `run_test_now.sh`**
- Updated output messages
- Single unified report reference

### No Changes Needed To

- `plot_k8s_metrics.py` - still generates standalone chart (optional)
- `monitor_during_test.sh` - still collects metrics
- Test execution workflow

## 🔧 Technical Details

### K8s Metrics Collection
```bash
# Automatically collected during test
kubectl top pods -n bcas-add-in -l app.kubernetes.io/name=bcas-add-in
```

**Output CSV:**
```csv
timestamp,pod,cpu_cores,memory_bytes,cpu_percent,memory_percent
2026-11-14T18:21:28Z,bcas-add-in-866f77677b-s8r7h,0.001,132120576,0.1,12.2
2026-11-14T18:21:28Z,bcas-add-in-866f77677b-z4fkh,0.001,132120576,0.1,12.3
...
```

### Statistics Calculated
```python
k8s_stats = {
    'avg_cpu': k8s_df['cpu_percent'].mean(),
    'max_cpu': k8s_df['cpu_percent'].max(),
    'min_cpu': k8s_df['cpu_percent'].min(),
    'avg_memory': k8s_df['memory_percent'].mean(),
    'max_memory': k8s_df['memory_percent'].max(),
    'min_memory': k8s_df['memory_percent'].min(),
    'avg_memory_mb': (k8s_df['memory_bytes'].mean() / 1024 / 1024),
    'max_memory_mb': (k8s_df['memory_bytes'].max() / 1024 / 1024)
}
```

## 📋 Comparison: Before vs After

### Before
```
📊 Reports:
   Performance: PERFORMANCE_REPORT.html
   K8s Metrics: k8s_metrics_chart.html     ← Separate file
   Locust:      results/report.html

Open:
   open PERFORMANCE_REPORT.html
   open k8s_metrics_chart.html             ← Two files
```

### After
```
📊 Reports:
   Performance: PERFORMANCE_REPORT.html (includes K8s metrics)
   Locust:      results/report.html

Open main report:
   open PERFORMANCE_REPORT.html            ← Single file
```

## ✨ Benefits

1. **Single Source of Truth**
   - One comprehensive report
   - All metrics in one place
   - Easier to share and analyze

2. **Automatic Correlation**
   - CPU/Memory shown alongside latency
   - Automatic bottleneck detection
   - Clear performance insights

3. **Always Available**
   - No extra steps needed
   - Works with existing workflow
   - Backward compatible (graceful degradation)

4. **Better Analysis**
   - Immediate visual correlation
   - Headroom calculations
   - I/O vs CPU detection

## 🧪 Tested With

**Test Run:** `runs/2026-11-14T18-21-28Z/`
- **Requests:** 821 total, 0 failures
- **Latency:** p95=1000ms, p99=1800ms
- **CPU:** 1.1% avg, 2.0% peak
- **Memory:** 12.3% avg, 126 MB
- **Analysis:** Low CPU + High latency = I/O bottleneck ✅

## 🎯 Result

Every performance test now provides complete observability:
- ✅ Client-side metrics (Locust)
- ✅ Server-side resources (K8s)
- ✅ Automatic correlation analysis
- ✅ Bottleneck detection
- ✅ Single unified report

**No manual correlation needed!**

---

**Generated:** 2026-11-14  
**Framework:** perf-framework v1.0
