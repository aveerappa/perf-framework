---
name: perf-execute
description: Use when ready to generate Locust test files and execute load tests - renders templates based on service type, runs Locust with configured parameters, and monitors test execution. Triggers on "run load test", "execute performance test", "start Locust", or after /perf-prepare completes.
---

# Performance Test Execution

Generate Locust test files from templates and execute load tests with real-time monitoring.

## When to Use

- After `/perf-prepare` has created config.json
- User wants to run the performance test
- Ready to execute load testing
- Need to generate Locust test files

## Prerequisites

- Configuration file exists (from `/perf-prepare`)
- Locust is installed (`pip install locust`)
- Service is accessible at base_url
- Credentials are valid

## Core Workflow

### 1. Load Configuration

```python
import json
from pathlib import Path

with open('config.json') as f:
    config = json.load(f)

service_type = config['service_type']
auth_type = config['auth_type']
base_url = config['base_url']
load_profile = config['load_profile']
```

### 2. Select Template

Based on service_type and auth_type:

| Service Type | Auth Type | Template |
|--------------|-----------|----------|
| rest-api | jwt | `templates/rest-api-jwt.py.j2` |
| rest-api | apikey | `templates/rest-api-apikey.py.j2` |
| graphql | bearer | `templates/graphql-bearer.py.j2` |
| Custom | * | Generate from base template |

### 3. Render Locust File

```python
from perf_framework.template_renderer import TemplateRenderer

renderer = TemplateRenderer()
template_path = f"templates/{service_type}-{auth_type}.py.j2"

# Render with config variables
locustfile_content = renderer.render(template_path, {
    'base_url': config['base_url'],
    'jwt_token': config['credentials'].get('jwt_token'),
    'api_key': config['credentials'].get('api_key'),
    'endpoints': config['endpoints']
})

# Save to locustfile.py
with open('locustfile.py', 'w') as f:
    f.write(locustfile_content)
```

### 4. Prepare Test Directory

Create directory structure:

```bash
runs/
  2026-11-14T15:30:00Z/
    locustfile.py        # Generated test
    config.json          # Configuration copy
    results/
      stats.csv          # Will be created by Locust
      failures.csv
      exceptions.csv
```

### 5. Execute Locust

Run with parameters from load_profile:

```python
from perf_framework.locust_runner import LocustRunner

runner = LocustRunner()

# Run Locust with config
result = runner.run(
    locustfile='locustfile.py',
    host=config['base_url'],
    users=config['load_profile']['users'],
    spawn_rate=config['load_profile']['spawn_rate'],
    run_time=f"{config['load_profile']['duration']}s",
    headless=True
)
```

**Command executed:**
```bash
locust -f locustfile.py \
  --host https://api.example.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 300s \
  --headless \
  --csv results/stats
```

### 6. Monitor Execution

Show real-time updates:
- Current user count
- Requests per second (RPS)
- Response time percentiles (p50, p95, p99)
- Error rate
- Progress bar

Example output:
```
Starting Locust test...
Users: 0 -> 100 (spawning at 10/s)
[=====>    ] 50/100 users

Current stats (60s elapsed):
  RPS: 450
  p50: 85ms
  p95: 320ms
  p99: 680ms
  Errors: 0.2%
```

### 7. Collect Results

When test completes:
```bash
runs/2026-11-14T15:30:00Z/results/
  stats.csv              # Request statistics
  stats_history.csv      # Timeline data
  failures.csv           # Failed requests
  exceptions.csv         # Exceptions log
```

## Dry Run Mode

For validation without actual load:

```bash
# Via CLI
perf-framework execute --config config.json --dry-run

# Shows what would be executed:
# - Template selected
# - Locustfile.py content preview
# - Locust command that would run
# - Does NOT actually run Locust
```

## Generated Locustfile Structure

Example for REST API with JWT:

```python
from locust import HttpUser, task
import json


class APIUser(HttpUser):
    host = "https://api.example.com"

    def on_start(self):
        """Set up authentication headers."""
        self.headers = {
            "Authorization": "Bearer eyJhbGc...",
            "Content-Type": "application/json"
        }

    @task(3)
    def create_order(self):
        """POST /api/v1/orders"""
        payload = {
            "item": "widget",
            "quantity": 1
        }
        self.client.post(
            "/api/v1/orders",
            headers=self.headers,
            json=payload
        )

    @task(7)
    def get_order(self):
        """GET /api/v1/orders/{id}"""
        self.client.get(
            "/api/v1/orders/123",
            headers=self.headers
        )
```

## Common Scenarios

### Scenario: Standard REST API Test
```
User: Run the performance test
Config: config.json exists with 100 users, 300s

Actions:
1. Load config.json
2. Select template: rest-api-jwt.py.j2
3. Render locustfile.py with JWT token
4. Create run directory: runs/2026-11-14T15:30:00Z/
5. Execute: locust --users 100 --run-time 300s --headless
6. Monitor: Show RPS and latency updates every 10s
7. Complete: Save results to runs/*/results/
8. Summary: "Test complete. 135,450 requests, p95 = 345ms, 0.1% errors"
```

### Scenario: GraphQL API Test
```
User: Execute GraphQL load test
Config: service_type = graphql, auth_type = bearer

Actions:
1. Select template: graphql-bearer.py.j2
2. Render with GraphQL queries from config
3. Run Locust with Bearer token auth
4. Monitor GraphQL-specific metrics
```

### Scenario: Smoke Test First
```
User: Run a quick smoke test first
Config: Normal config has 200 users

Actions:
1. Ask: "Run smoke test? (10 users, 60s)"
2. User confirms
3. Override config temporarily: users=10, duration=60
4. Run smoke test
5. Show results
6. Ask: "Proceed with full test (200 users, 600s)?"
```

## Error Handling

### Connection Errors
```
Error: Failed to connect to https://api.example.com
Actions:
- Verify base_url is correct
- Check service is running
- Test connectivity: curl https://api.example.com
```

### Authentication Errors
```
Error: 401 Unauthorized on all requests
Actions:
- Verify credentials in config.json
- Check token hasn't expired
- Test single request: curl -H "Authorization: Bearer ..."
```

### High Error Rate During Test
```
Warning: Error rate > 5% (current: 12%)
Actions:
- Pause test and investigate
- Reduce load (fewer users or lower spawn rate)
- Check service logs for issues
```

## Execution Checklist

Before running:

- [ ] config.json exists and is valid
- [ ] Locust is installed
- [ ] Service is accessible
- [ ] Credentials are current (not expired)
- [ ] Enough time allocated for test
- [ ] Monitoring ready (Prometheus/New Relic if used)

During test:

- [ ] Monitor RPS and latency
- [ ] Watch error rate
- [ ] Check service health
- [ ] Verify user ramp-up is smooth

After test:

- [ ] Results saved to runs/ directory
- [ ] CSV files generated
- [ ] No critical errors in exceptions.csv
- [ ] Ready for `/perf-report`

## Output Structure

```
runs/2026-11-14T15:30:00Z/
├── locustfile.py           # Generated test file
├── config.json             # Configuration used
└── results/
    ├── stats.csv           # Per-endpoint statistics
    ├── stats_history.csv   # Timeline data
    ├── failures.csv        # Failed requests
    └── exceptions.csv      # Exception details
```

## Next Steps

After execution completes:
1. Review results in runs/*/results/
2. Run `/perf-report` to generate HTML report with charts
3. Analyze against SLA thresholds
4. Check Prometheus/New Relic for backend metrics

## References

- LocustRunner: `cli/perf_framework/locust_runner.py`
- TemplateRenderer: `cli/perf_framework/template_renderer.py`
- Templates: `templates/` directory
- Locust docs: https://docs.locust.io/
