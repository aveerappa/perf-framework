# Performance Testing Framework

Lightweight framework for REST API performance testing with automatic Kubernetes metrics collection.

## Features

- 🚀 **Quick Setup** - JSON configuration, no code needed
- 📊 **Unified Reports** - Performance + K8s CPU/Memory in one HTML report
- ✅ **Pre-flight Validation** - Catches issues before running tests
- 🎯 **SLA Tracking** - Automatic threshold validation
- ☸️ **K8s Integration** - Automatic pod resource monitoring
- 📈 **Interactive Charts** - Plotly visualizations

## Quick Start

### 1. Install Dependencies

```bash
pip install locust pandas plotly jinja2
```

### 2. Run Performance Test

```bash
# Quick test with K8s metrics (1 minute)
./run_test.sh bcas-add-in-config.json 60
```

This automatically:
- Collects K8s CPU/Memory metrics every 5 seconds
- Runs Locust load test
- Generates unified HTML report
- Opens report in browser

### 3. View Results

The report includes:
- **Performance:** Requests, RPS, latency (p50/p95/p99), errors
- **K8s Metrics:** CPU & Memory utilization per pod
- **Analysis:** Automatic bottleneck detection (I/O vs CPU)
- **SLA Status:** Pass/fail for each threshold

## Configuration

Create `config.json` (or use `projects/bcas-add-in-config.json`):

```json
{
  "service_name": "my-api",
  "base_url": "https://api.example.com",
  "credentials": {
    "jwt_token": "eyJhbGc..."
  },
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/v1/health",
      "weight": 10,
      "requires_auth": false
    },
    {
      "method": "POST",
      "path": "/api/v1/orders",
      "weight": 3,
      "requires_auth": true,
      "payload": {"item": "test"}
    }
  ],
  "load_profile": {
    "users": 10,
    "spawn_rate": 10,
    "duration": 60
  },
  "sla": {
    "p95_ms": 500,
    "error_rate": 0.01
  }
}
```

## Usage via Claude Code Skills

```bash
# 1. Analyze service
/perf-analyze

# 2. Prepare configuration (with validation)
/perf-prepare

# 3. Execute test
/perf-execute for 1 min

# 4. Generate report
/perf-report
```

## Manual Usage

### Validate Configuration

```bash
python validate_config.py config.json
```

Checks:
- ✅ JWT token not expired
- ✅ Base URL reachable
- ✅ Authentication working
- ✅ Sample endpoints responding

### Run Test with K8s Metrics (Multi-Service)

K8s metrics are **automatically collected** during tests! Monitors both:
- **Primary service**: bcas-add-in (service being tested)
- **Downstream services**: web-core-api (backend dependency)

```bash
# Simple: All-in-one test runner (auto-collects K8s metrics from both services)
./run_test.sh bcas-add-in-config.json 300

# Report is generated automatically at:
# runs/<timestamp>/PERFORMANCE_REPORT.html
```

### View Report

```bash
open runs/<timestamp>/PERFORMANCE_REPORT.html
```

## Project Structure

```
perf-framework/
├── README.md                      # This file
├── run_test.sh                    # End-to-end test runner (validate → locust → report)
├── validate_config.py             # Pre-flight validation
├── monitor_multi_service.sh       # K8s CPU/memory collector (bcas-add-in + web-core-api)
├── monitor_progress.sh            # Live stats line every 60s during a run
├── generate_enterprise_report.py  # Unified HTML report (performance + K8s)
├── plot_k8s_metrics.py            # Combined K8s chart
├── plot_k8s_metrics_individual.py # Per-service K8s charts (used by the report)
├── barracuda-logo.jpg             # Embedded in the report header
├── templates/
│   └── rest-api-jwt.py.j2        # Locust template
├── docs/
│   ├── K8S_METRICS_GUIDE.md      # Detailed K8s guide
│   └── K8S_METRICS_INTEGRATED.md # Integration details
├── projects/
│   ├── bcas-add-in-config.json   # Example configuration
│   └── bcas-add-in-test-plan.yaml
└── runs/
    └── <timestamp>/              # Test results
        ├── PERFORMANCE_REPORT.html
        ├── k8s_metrics.csv
        └── results/
```

## Report Contents

### Summary Cards
- Total Requests
- Success Rate
- Error Rate
- P50/P95/P99 Latency
- **CPU Usage** (avg & peak)
- **Memory Usage** (avg & MB)

### Performance Charts
- Response Time Percentiles
- Requests Per Second
- Error Rate
- Request Distribution
- Endpoint Latency

### Kubernetes Metrics Section
- **Resource Analysis Box**
  - CPU/Memory statistics
  - Headroom calculation
  - Bottleneck detection
- **CPU Utilization Chart** (per-pod, with threshold)
- **Memory Usage Chart** (per-pod, timeline)

### SLA Compliance
- Pass/fail per threshold
- Visual indicators

## Kubernetes Prerequisites

```bash
# 1. Verify kubectl access
kubectl get pods -n <namespace>

# 2. AWS SSO login (if needed)
aws sso login --profile YOUR_PROFILE

# 3. Check pod labels
kubectl get pods -n <namespace> --show-labels
```

Pods must have label: `app.kubernetes.io/name=<service-name>`

## Troubleshooting

### JWT Token Expired
```
❌ JWT token expired (expires in -5 minutes)
Fix: Update credentials.jwt_token in config.json
```

### kubectl Access Failed
```
❌ kubectl access failed
Fix: aws sso login --profile YOUR_PROFILE
```

### No Pods Found
```
❌ No pods found with label app.kubernetes.io/name=service
Fix: kubectl get pods -n <namespace> --show-labels
```

### SLA Failed
```
❌ SLA FAILED: p95: 1000ms > 500ms threshold
Analysis: Low CPU (1.1%) + High latency = I/O bottleneck
Action: Check external services (S3, Elasticsearch, databases)
```

## Documentation

- **[K8S_METRICS_GUIDE.md](docs/K8S_METRICS_GUIDE.md)** - Comprehensive Kubernetes metrics guide (collection methods, workflows, correlation analysis)
- **[K8S_METRICS_INTEGRATED.md](docs/K8S_METRICS_INTEGRATED.md)** - Integration summary and technical details

## Examples

See `projects/` directory:
- `bcas-add-in-config.json` - Full API configuration
- `bcas-add-in-test-plan.yaml` - Test plan template

## License

MIT

## Created

2026-11-14
