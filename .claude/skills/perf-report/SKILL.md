---
name: perf-report
description: Use when generating performance test reports after load test execution - analyzes Locust results, fetches Prometheus/New Relic metrics, creates HTML reports with Plotly charts, and evaluates against SLA thresholds. Triggers on "generate report", "analyze test results", "show performance metrics", or after /perf-execute completes.
---

# Performance Test Reporting

Generate comprehensive HTML reports with charts analyzing load test results and backend metrics.

## When to Use

- After `/perf-execute` has completed a test run
- User wants to analyze performance test results
- Need to compare results against SLA thresholds
- Generating reports for stakeholders

## Prerequisites

- Test run directory exists in `runs/`
- Locust CSV files generated (stats.csv, stats_history.csv)
- (Optional) Prometheus or New Relic access for backend metrics
- Run ID or timestamp to identify test run

## Core Workflow

### 1. Identify Test Run

```python
from pathlib import Path

# Find latest run or use specified run-id
runs_dir = Path('runs')
latest_run = sorted(runs_dir.iterdir())[-1]
run_id = latest_run.name  # e.g., "2026-11-14T15:30:00Z"
```

### 2. Load Test Results

```python
import pandas as pd

results_dir = Path(f'runs/{run_id}/results')

# Load Locust statistics
stats = pd.read_csv(results_dir / 'stats.csv')
history = pd.read_csv(results_dir / 'stats_history.csv')
failures = pd.read_csv(results_dir / 'failures.csv')
exceptions = pd.read_csv(results_dir / 'exceptions.csv')

# Load original config
import json
with open(f'runs/{run_id}/config.json') as f:
    config = json.load(f)
```

### 3. Calculate Key Metrics

```python
from perf_framework.report_generator import ReportGenerator

generator = ReportGenerator()

metrics = {
    'total_requests': stats['Request Count'].sum(),
    'total_failures': stats['Failure Count'].sum(),
    'avg_response_time': stats['Average Response Time'].mean(),
    'p50': stats['50%'].median(),
    'p95': stats['95%'].median(),
    'p99': stats['99%'].median(),
    'requests_per_second': stats['Requests/s'].mean(),
    'error_rate': stats['Failure Count'].sum() / stats['Request Count'].sum()
}
```

### 4. Fetch Backend Metrics (Optional)

#### From Prometheus

```python
from perf_framework.prometheus_client import PrometheusClient

prom = PrometheusClient(url='http://prometheus.company.com')

# Query during test window
start_time = config['start_timestamp']
end_time = config['end_timestamp']

backend_metrics = {
    'cpu_usage': prom.query_range(
        'container_cpu_usage_seconds_total',
        start=start_time,
        end=end_time
    ),
    'memory_usage': prom.query_range(
        'container_memory_usage_bytes',
        start=start_time,
        end=end_time
    ),
    'request_duration': prom.query_range(
        'http_request_duration_seconds',
        start=start_time,
        end=end_time
    )
}
```

#### From New Relic

```python
from perf_framework.newrelic_client import NewRelicClient

nr = NewRelicClient(api_key='YOUR_API_KEY')

apm_data = nr.query_nrql(
    f"SELECT average(duration), percentile(duration, 95, 99) "
    f"FROM Transaction "
    f"WHERE appName = 'orders-api' "
    f"SINCE '{start_time}' UNTIL '{end_time}'"
)
```

### 5. Generate Charts

Using Plotly for interactive HTML charts:

```python
import plotly.graph_objects as go

# Response Time Over Time
fig_latency = go.Figure()
fig_latency.add_trace(go.Scatter(
    x=history['Timestamp'],
    y=history['95%'],
    name='p95',
    line=dict(color='orange')
))
fig_latency.add_trace(go.Scatter(
    x=history['Timestamp'],
    y=history['50%'],
    name='p50',
    line=dict(color='blue')
))

# RPS Over Time
fig_rps = go.Figure()
fig_rps.add_trace(go.Scatter(
    x=history['Timestamp'],
    y=history['Requests/s'],
    fill='tozeroy',
    name='RPS'
))

# Error Rate Over Time
fig_errors = go.Figure()
fig_errors.add_trace(go.Scatter(
    x=history['Timestamp'],
    y=(history['Failure Count'] / history['Request Count']) * 100,
    line=dict(color='red'),
    name='Error %'
))
```

### 6. Evaluate SLA Compliance

```python
sla = config.get('sla', {})

compliance = {
    'p95_threshold': sla.get('p95_ms', 500),
    'p95_actual': metrics['p95'],
    'p95_pass': metrics['p95'] < sla.get('p95_ms', 500),
    
    'error_rate_threshold': sla.get('error_rate', 0.01),
    'error_rate_actual': metrics['error_rate'],
    'error_rate_pass': metrics['error_rate'] < sla.get('error_rate', 0.01)
}
```

### 7. Generate HTML Report

```python
html_report = generator.render_html({
    'run_id': run_id,
    'config': config,
    'metrics': metrics,
    'compliance': compliance,
    'charts': {
        'latency': fig_latency.to_html(include_plotlyjs='cdn'),
        'rps': fig_rps.to_html(include_plotlyjs=False),
        'errors': fig_errors.to_html(include_plotlyjs=False)
    },
    'backend_metrics': backend_metrics,
    'failures': failures.to_html() if not failures.empty else None
})

# Save report
report_path = f'runs/{run_id}/report.html'
with open(report_path, 'w') as f:
    f.write(html_report)
```

## Report Structure

### Executive Summary
- Run ID and timestamp
- Test duration
- Total requests
- Average RPS
- Overall result: ✅ PASS or ❌ FAIL

### Key Metrics Table

| Metric | Value | SLA | Status |
|--------|-------|-----|--------|
| p50 latency | 125ms | < 200ms | ✅ PASS |
| p95 latency | 345ms | < 500ms | ✅ PASS |
| p99 latency | 780ms | < 1000ms | ✅ PASS |
| Error rate | 0.3% | < 1% | ✅ PASS |
| Throughput | 450 RPS | > 400 RPS | ✅ PASS |

### Interactive Charts

1. **Response Time Over Time**
   - p50, p95, p99 lines
   - SLA threshold line
   - Hover for exact values

2. **Requests Per Second**
   - RPS over test duration
   - User ramp-up visible
   - Peak RPS highlighted

3. **Error Rate Over Time**
   - Percentage errors
   - Spike detection
   - Error types breakdown

4. **Request Distribution**
   - Per-endpoint request counts
   - Weighted vs actual distribution
   - Response time by endpoint

### Backend Metrics (if available)

5. **CPU Usage**
   - Container/pod CPU %
   - Correlation with RPS

6. **Memory Usage**
   - Memory consumption
   - Leak detection

7. **Backend Latency**
   - Database query time
   - External API calls
   - Cache hit rate

### Failures Analysis

If failures occurred:
- Count by endpoint
- Error messages
- First occurrence timestamp
- Pattern identification

## Common Scenarios

### Scenario: Standard Report Generation
```
User: Generate report for latest test
Runs: runs/2026-11-14T15:30:00Z/ exists

Actions:
1. Load results from latest run directory
2. Calculate metrics from stats.csv
3. Generate charts from stats_history.csv
4. Evaluate against SLA (p95 < 500ms, errors < 1%)
5. Create HTML report with Plotly charts
6. Save to runs/2026-11-14T15:30:00Z/report.html
7. Show summary: "✅ Test PASSED. p95: 345ms, errors: 0.3%"
8. Provide path to report
```

### Scenario: Report with Prometheus Data
```
User: Generate report with backend metrics
Prometheus: Available at http://prometheus.company.com

Actions:
1. Load Locust results
2. Connect to Prometheus
3. Query CPU, memory, latency for test window
4. Generate combined frontend + backend charts
5. Show correlation between load and resource usage
6. Highlight bottlenecks (e.g., CPU spike at 150 users)
```

### Scenario: Failed SLA
```
Results: p95 = 850ms (threshold: 500ms)

Report shows:
❌ TEST FAILED
- p95 latency: 850ms > 500ms threshold
- p99 latency: 1500ms > 1000ms threshold
- Error rate: 0.2% ✅ PASS

Recommendations:
- Review backend logs during peak load
- Check for database slow queries
- Consider caching frequently accessed data
```

### Scenario: High Error Rate
```
Results: 15% error rate

Report includes:
- Error breakdown by type (401: 2%, 500: 8%, 503: 5%)
- Timeline showing errors started at 200 users
- Top failing endpoints: POST /api/orders (12% errors)

Suggested actions:
- Check service capacity limits
- Review rate limiting configuration
- Analyze 500 errors in service logs
```

## Metrics Reference

### Locust Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| Request Count | Total requests sent | Matches expected load |
| Failure Count | Failed requests | < 1% of total |
| Average Response Time | Mean latency | < 200ms |
| p50 | Median response time | < 100ms |
| p95 | 95th percentile | < 500ms |
| p99 | 99th percentile | < 1000ms |
| Requests/s | Throughput | Meets target RPS |

### Backend Metrics (Prometheus)

| Metric | Query | Target |
|--------|-------|--------|
| CPU Usage | `container_cpu_usage_seconds_total` | < 80% |
| Memory | `container_memory_usage_bytes` | < 80% limit |
| Request Duration | `http_request_duration_seconds` | Matches Locust p95 |
| Active Connections | `http_connections_active` | < max connections |

## Report Output

```bash
runs/2026-11-14T15:30:00Z/
├── config.json
├── locustfile.py
├── report.html              # ← Generated report
└── results/
    ├── stats.csv
    ├── stats_history.csv
    ├── failures.csv
    └── exceptions.csv
```

## Opening the Report

```bash
# Open in browser
open runs/2026-11-14T15:30:00Z/report.html

# Or serve with Python
cd runs/2026-11-14T15:30:00Z
python -m http.server 8000
# Visit http://localhost:8000/report.html
```

## Comparison Reports

For regression testing, compare multiple runs:

```python
# Compare two test runs
generator.compare_runs([
    'runs/2026-11-14T15:30:00Z',
    'runs/2026-11-15T10:00:00Z'
])

# Shows:
# - Metric changes (p95: 345ms → 280ms, -19% ✅)
# - Performance trend
# - Regression detection
```

## Sharing Reports

HTML reports are self-contained:
- Embed Plotly charts (no external dependencies)
- Include all data inline
- Can be emailed or uploaded to S3/docs site
- Interactive without server required

## Next Steps

After report generation:
1. Review SLA compliance
2. Identify bottlenecks from charts
3. Check failure patterns if error rate high
4. Correlate with backend metrics
5. Share report with team
6. Plan optimizations if needed
7. Re-run tests after changes

## References

- ReportGenerator: `cli/perf_framework/report_generator.py`
- PrometheusClient: `cli/perf_framework/prometheus_client.py`
- NewRelicClient: `cli/perf_framework/newrelic_client.py`
- Plotly docs: https://plotly.com/python/
- Locust stats format: https://docs.locust.io/en/stable/retrieving-stats.html
